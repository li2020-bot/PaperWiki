import json
from paperwiki.config import Config, PathsConfig, AIConfig, ReportConfig, ProcessingConfig
from paperwiki.config import OllamaConfig
from paperwiki.report_generator import ReportGenerator, SYSTEM_PROMPT, REPORT_TEMPLATE


def _make_config():
    ai = AIConfig(backend="ollama")
    ai.ollama = OllamaConfig(base_url="http://localhost:11434", model="qwen3")
    return Config(
        paths=PathsConfig(raw_papers="/tmp/papers", obsidian_vault="/tmp/vault"),
        ai=ai,
        report=ReportConfig(language="zh-CN"),
        processing=ProcessingConfig(temp_dir="/tmp/test"),
    )


class FakeAIClient:
    def __init__(self, response_json: dict):
        self.response_json = response_json
        self.last_messages = None

    def chat(self, messages: list[dict]) -> str:
        self.last_messages = messages
        return json.dumps(self.response_json, ensure_ascii=False)


def test_system_prompt_contains_json_requirements():
    assert "JSON" in SYSTEM_PROMPT
    assert "summary" in SYSTEM_PROMPT
    assert "entities" in SYSTEM_PROMPT
    assert "references" in SYSTEM_PROMPT


def test_generate_report_parses_json_and_renders():
    config = _make_config()
    fake_response = {
        "title": "Deep Learning Advances",
        "summary": "This paper explores recent advances in deep learning.",
        "entities": [
            {"name": "Transformer", "type": "方法"},
            {"name": "Attention", "type": "概念"},
        ],
        "references": ["Vaswani et al., 2017", "Brown et al., 2020"],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)

    markdown = generator.generate_report(
        paper_text="Some paper text...",
        metadata={"title": "Deep Learning Advances", "author": "John Doe"},
        source_file="test.pdf",
    )

    assert "# Deep Learning Advances" in markdown
    assert "This paper explores recent advances" in markdown
    assert "[[Transformer]]" in markdown
    assert "(方法)" in markdown
    assert "[[Attention]]" in markdown
    assert "Vaswani et al., 2017" in markdown
    assert "[[raw/Deep Learning Advances|查看原始提取文本]]" in markdown
    assert "test.pdf" in markdown


def test_generate_report_includes_all_entities():
    config = _make_config()
    fake_response = {
        "title": "Test",
        "summary": "Test summary.",
        "entities": [
            {"name": "CNN", "type": "方法"},
            {"name": "RNN", "type": "方法"},
            {"name": "Backpropagation", "type": "术语"},
            {"name": "Geoffrey Hinton", "type": "人物"},
        ],
        "references": [],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)
    markdown = generator.generate_report("text", {"title": "Test"}, "test.pdf")

    assert "[[CNN]]" in markdown
    assert "[[RNN]]" in markdown
    assert "[[Backpropagation]]" in markdown
    assert "[[Geoffrey Hinton]]" in markdown


def test_prompt_includes_paper_text():
    config = _make_config()
    fake_response = {
        "title": "Test",
        "summary": "Test.",
        "entities": [],
        "references": [],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)
    generator.generate_report("This is the paper content.", {"title": "Test"}, "test.pdf")

    user_message = fake_client.last_messages[-1]["content"]
    assert "This is the paper content." in user_message
