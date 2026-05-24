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
            "tldr": "提出Transformer架构，完全基于注意力机制，在机器翻译等任务上取得突破性进展。",
            "background": "传统序列建模依赖循环或卷积网络，计算效率低，难以捕捉长距离依赖。",
            "method": "提出基于多头自注意力机制的编码器-解码器架构，并行计算序列所有位置的关联。",
            "key_findings": [
                "在WMT机器翻译任务上达到SOTA，训练时间大幅缩短。",
                "注意力机制可以学习到丰富的句法和语义关系。",
            ],
            "entities": [
                {"name": "Transformer", "type": "方法", "section": "3. Model Architecture", "brief": "基于自注意力的序列模型"},
                {"name": "Self-Attention", "type": "概念", "section": "2. Background", "brief": "序列自身不同位置的注意力计算"},
                {"name": "Multi-Head Attention", "type": "概念", "section": "3. Model Architecture", "brief": "多组注意力并行计算"},
                {"name": "Vaswani", "type": "人物", "section": "1. Introduction", "brief": "Transformer论文第一作者"},
            ],
            "keywords": ["Transformer", "attention", "self-attention", "machine translation"],
            "references": [
                "Vaswani et al., Attention Is All You Need, NeurIPS 2017",
                "Bahdanau et al., Neural Machine Translation by Jointly Learning to Align and Translate, ICLR 2015",
            ],
        }

        fake_ai = FakeAIDetermined(fake_response)
        result = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result is True

        report_path = os.path.join(vault_dir, "wiki", "Attention Is All You Need.md")

        assert os.path.exists(report_path)

        with open(report_path, "r") as f:
            report = f.read()

        assert "## TL;DR" in report
        assert "Transformer" in report
        assert "[[Transformer]]" in report
        assert "[[Self-Attention]]" in report
        assert "[[Multi-Head Attention]]" in report
        assert "[[Vaswani]]" in report
        assert "Vaswani et al., Attention Is All You Need, NeurIPS 2017" in report
        assert "自动生成于" in report

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
            "tldr": "探讨了深度学习在NLP中的应用进展。",
            "background": "NLP任务需要强大的特征表示能力。",
            "method": "采用深度神经网络进行文本特征学习和语义建模。",
            "key_findings": ["本文探讨了深度学习在NLP中的应用。"],
            "entities": [
                {"name": "深度学习", "type": "方法", "section": "1. Introduction", "brief": "多层神经网络学习范式"},
                {"name": "NLP", "type": "术语", "section": "1. Introduction", "brief": "自然语言处理领域"},
            ],
            "keywords": ["深度学习", "自然语言处理", "NLP"],
            "references": [],
        }

        fake_ai = FakeAIDetermined(fake_response)
        result = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result is True

        report_path = os.path.join(vault_dir, "wiki", "深度学习在自然语言处理中的应用研究.md")

        assert os.path.exists(report_path)

        with open(report_path, "r") as f:
            report = f.read()
        assert "[[深度学习]]" in report
        assert "[[NLP]]" in report
