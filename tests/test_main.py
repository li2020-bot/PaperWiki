import os
import tempfile
import fitz
from paperwiki.main import process_pdf


def _create_test_pdf(dir_path: str, filename: str, text: str):
    doc = fitz.open()
    doc.new_page()
    doc[0].insert_text((72, 72), text, fontsize=12)
    doc.set_metadata({"title": "Test Paper", "author": "Test Author"})
    pdf_path = os.path.join(dir_path, filename)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


class FakeAIClient:
    def chat(self, messages):
        import json
        return json.dumps({
            "title": "Test Paper",
            "tldr": "A quick summary of the paper.",
            "background": "Research background.",
            "method": "Core method description.",
            "key_findings": ["A key contribution."],
            "entities": [{"name": "Test Entity", "type": "概念", "section": "1. Intro", "brief": "A test entity"}],
            "keywords": ["deep learning", "transformer"],
            "references": ["Test Ref, 2026"],
        })

    @property
    def backend(self):
        return "test"


class FakeConfig:
    class Paths:
        def __init__(self, raw_papers, obsidian_vault):
            self.raw_papers = raw_papers
            self.obsidian_vault = obsidian_vault
            self.wiki_subdir = "wiki"
    class AI:
        backend = "test"
    class Report:
        multi_angle = False
    class Processing:
        temp_dir = "/tmp/paperwiki_test"

    def __init__(self, raw_papers, obsidian_vault):
        self.paths = self.Paths(raw_papers, obsidian_vault)
        self.ai = self.AI()
        self.report = self.Report()
        self.processing = self.Processing()


def test_process_pdf_creates_report():
    with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as vault_dir:
        config = FakeConfig(raw_dir, vault_dir)
        pdf_path = _create_test_pdf(raw_dir, "test_paper.pdf", "Paper content for testing.")

        fake_ai = FakeAIClient()
        result = process_pdf(pdf_path, config, ai_client=fake_ai)

        report_path = os.path.join(vault_dir, "wiki", "Test Paper.md")

        assert os.path.exists(report_path), f"Report not found at {report_path}"

        with open(report_path, "r") as f:
            report = f.read()
        assert "A quick summary of the paper." in report
        assert "Test Entity" in report
        assert "[[Test Entity]]" in report


def test_process_pdf_skips_already_processed():
    with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as vault_dir:
        config = FakeConfig(raw_dir, vault_dir)
        pdf_path = _create_test_pdf(raw_dir, "test.pdf", "Content.")

        fake_ai = FakeAIClient()
        result1 = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result1 is True

        result2 = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result2 is False
