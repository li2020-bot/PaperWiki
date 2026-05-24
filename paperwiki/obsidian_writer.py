import os
import re
import json
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger("paperwiki.obsidian_writer")


class ObsidianWriter:
    def __init__(self, obsidian_vault: str, wiki_subdir: str,
                 processed_path: str = "processed_files.json"):
        self.vault = obsidian_vault
        self.wiki_dir = os.path.join(obsidian_vault, wiki_subdir)
        self.processed_path = processed_path
        self._ensure_dirs()
        self._processed = self._load_processed()

    def _ensure_dirs(self):
        os.makedirs(self.wiki_dir, exist_ok=True)

    def _sanitize_filename(self, name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', "_", name)

    @staticmethod
    def _file_hash(filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_processed(self) -> dict:
        if os.path.exists(self.processed_path):
            try:
                with open(self.processed_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            except json.JSONDecodeError:
                logger.warning(
                    "Corrupt processed file at %s, resetting.", self.processed_path
                )
                return {}
        return {}

    def _save_processed(self):
        with open(self.processed_path, "w", encoding="utf-8") as f:
            json.dump(self._processed, f, indent=2, ensure_ascii=False)

    def is_processed(self, filepath: str) -> bool:
        if filepath not in self._processed:
            return False
        if not os.path.exists(filepath):
            return True
        file_hash = self._file_hash(filepath)
        return self._processed[filepath]["hash"] == file_hash

    def _mark_processed(self, filepath: str, output_file: str):
        file_hash = self._file_hash(filepath)
        self._processed[filepath] = {
            "hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "output_file": output_file,
        }
        self._save_processed()

    def save_report(self, report_markdown: str, title: str, source_file: str):
        filename = self._sanitize_filename(title) + ".md"
        filepath = os.path.join(self.wiki_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_markdown)
        self._mark_processed(source_file, filename)
        logger.info("Report saved: %s", filepath)
