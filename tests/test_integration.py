import os
import tempfile
import fitz
from paperwiki.main import process_pdf


def _create_pdf(dir_path: str, filename: str, title: str, text: str):
    doc = fitz.open()
    doc.new_page()
    doc[0].insert_text((72, 72), text, fontsize=12)
    doc.set_metadata({"title": title, "author": "Test Author"})
    pdf_path = os.path.join(dir_path, filename)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


class FakeAIDetermined:
    """Fake AI that returns a specific response."""
    def __init__(self, response):
        self.response = response
        self.call_count = 0

    def chat(self, messages):
        self.call_count += 1
        import json
        return json.dumps(self.response, ensure_ascii=False)

    @property
    def backend(self):
        return "test"


class FakeConfig:
    class Paths:
        def __init__(self, raw_papers, obsidian_vault):
            self.raw_papers = raw_papers
            self.obsidian_vault = obsidian_vault
            self.wiki_subdir = "wiki"
            self.raw_subdir = "raw"
    class AI:
        backend = "test"
    class Report:
        language = "zh-CN"
    class Processing:
        temp_dir = "/tmp/paperwiki_test"

    def __init__(self, raw_papers, obsidian_vault):
        self.paths = self.Paths(raw_papers, obsidian_vault)
        self.ai = self.AI()
        self.report = self.Report()
        self.processing = self.Processing()


def test_full_pipeline():
    with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as vault_dir:
        config = FakeConfig(raw_dir, vault_dir)
        pdf_path = _create_pdf(
            raw_dir, "attention_is_all_you_need.pdf",
            "Attention Is All You Need",
            "The dominant sequence transduction models are based on complex recurrent "
            "or convolutional neural networks. We propose a new simple network architecture, "
            "the Transformer, based solely on attention mechanisms."
        )

        fake_response = {
            "title": "Attention Is All You Need",
            "summary": "本文提出了Transformer架构，完全基于注意力机制，摒弃了传统的循环和卷积结构。",
            "entities": [
                {"name": "Transformer", "type": "方法"},
                {"name": "Self-Attention", "type": "概念"},
                {"name": "Multi-Head Attention", "type": "概念"},
                {"name": "Vaswani", "type": "人物"},
            ],
            "references": [
                "Vaswani et al., Attention Is All You Need, NeurIPS 2017",
                "Bahdanau et al., Neural Machine Translation by Jointly Learning to Align and Translate, ICLR 2015",
            ],
        }

        fake_ai = FakeAIDetermined(fake_response)
        result = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result is True

        report_path = os.path.join(vault_dir, "wiki", "Attention Is All You Need.md")
        raw_path = os.path.join(vault_dir, "wiki", "raw", "Attention Is All You Need.md")

        assert os.path.exists(report_path)
        assert os.path.exists(raw_path)

        with open(report_path, "r") as f:
            report = f.read()

        assert "# Attention Is All You Need" in report
        assert "Transformer" in report
        assert "[[Transformer]]" in report
        assert "[[Self-Attention]]" in report
        assert "[[Multi-Head Attention]]" in report
        assert "[[Vaswani]]" in report
        assert "[[raw/Attention Is All You Need" in report
        assert "Vaswani et al., Attention Is All You Need, NeurIPS 2017" in report
        assert "自动生成于" in report

        with open(raw_path, "r") as f:
            raw = f.read()
        assert "Attention Is All You Need" in raw
        assert "The dominant sequence transduction models" in raw

        result2 = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result2 is False


def test_pipeline_with_non_ascii_title():
    with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as vault_dir:
        config = FakeConfig(raw_dir, vault_dir)
        pdf_path = _create_pdf(
            raw_dir, "paper.pdf",
            "深度学习在自然语言处理中的应用研究",
            "This paper explores deep learning applications in NLP."
        )

        fake_response = {
            "title": "深度学习在自然语言处理中的应用研究",
            "summary": "本文探讨了深度学习在NLP中的应用。",
            "entities": [{"name": "深度学习", "type": "方法"}, {"name": "NLP", "type": "术语"}],
            "references": [],
        }

        fake_ai = FakeAIDetermined(fake_response)
        result = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result is True

        report_path = os.path.join(vault_dir, "wiki", "深度学习在自然语言处理中的应用研究.md")
        raw_path = os.path.join(vault_dir, "wiki", "raw", "深度学习在自然语言处理中的应用研究.md")

        assert os.path.exists(report_path)
        assert os.path.exists(raw_path)

        with open(report_path, "r") as f:
            report = f.read()
        assert "[[深度学习]]" in report
        assert "[[NLP]]" in report
