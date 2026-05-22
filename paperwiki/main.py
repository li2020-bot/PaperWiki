import os
import sys
import time
import logging
from paperwiki.config import load_config
from paperwiki.pdf_extractor import extract_text
from paperwiki.ai_client import AIClient
from paperwiki.report_generator import ReportGenerator
from paperwiki.obsidian_writer import ObsidianWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("paperwiki")


def _log_error(error_log_path: str, message: str):
    with open(error_log_path, "a", encoding="utf-8") as f:
        f.write(message + "\n")
    logger.error(message)


def process_pdf(pdf_path: str, config, ai_client=None) -> bool:
    if not pdf_path.lower().endswith(".pdf"):
        return False

    error_log_path = os.path.join(config.paths.obsidian_vault, "error.log")
    processed_path = os.path.join(config.paths.obsidian_vault, ".paperwiki_processed.json")

    ai = ai_client or AIClient(config)
    writer = ObsidianWriter(
        config.paths.obsidian_vault,
        config.paths.wiki_subdir,
        config.paths.raw_subdir,
        processed_path=processed_path,
    )

    if writer.is_processed(pdf_path):
        logger.info(f"Skipping already processed: {pdf_path}")
        return False

    logger.info(f"Processing: {pdf_path}")

    try:
        text, metadata = extract_text(pdf_path)
    except Exception as e:
        _log_error(error_log_path, f"PDF extraction failed for {pdf_path}: {e}")
        return False

    title = metadata.get("title") or "Untitled"
    writer.save_raw_text(text, title, pdf_path)

    try:
        generator = ReportGenerator(config, ai)
        report = generator.generate_report(text, metadata, source_file=pdf_path)
    except Exception as e:
        _log_error(error_log_path, f"AI report generation failed for {pdf_path}: {e}")
        return False

    try:
        writer.save_report(report, title, pdf_path)
    except Exception as e:
        _log_error(error_log_path, f"Failed to write output for {pdf_path}: {e}")
        return False

    logger.info(f"Completed: {pdf_path}")
    return True


def main():
    config = load_config()

    os.makedirs(config.paths.raw_papers, exist_ok=True)
    os.makedirs(config.paths.obsidian_vault, exist_ok=True)
    os.makedirs(config.processing.temp_dir, exist_ok=True)

    error_log_path = os.path.join(config.paths.obsidian_vault, "error.log")

    logger.info(f"Watching: {config.paths.raw_papers}")
    logger.info(f"Output: {config.paths.obsidian_vault}/{config.paths.wiki_subdir}")
    logger.info(f"AI Backend: {config.ai.backend}")

    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class PDFHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            try:
                time.sleep(1)
                process_pdf(event.src_path, config)
            except Exception as e:
                _log_error(error_log_path, f"Handler crashed for {event.src_path}: {e}")

    observer = Observer()
    observer.schedule(PDFHandler(), config.paths.raw_papers, recursive=False)
    observer.start()

    logger.info("PaperWiki is running. Press Ctrl+C to stop.")
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        logger.info("PaperWiki stopped.")
    observer.join()


if __name__ == "__main__":
    main()
