import json
from paperwiki.config import Config, PathsConfig, AIConfig, ReportConfig, ProcessingConfig
from paperwiki.config import OllamaConfig
from paperwiki.report_generator import ReportGenerator, SYSTEM_PROMPT, REPORT_TEMPLATE


def _make_config(multi_angle=False):
    ai = AIConfig(backend="ollama")
    ai.ollama = OllamaConfig(base_url="http://localhost:11434", model="qwen3")
    return Config(
        paths=PathsConfig(raw_papers="/tmp/papers", obsidian_vault="/tmp/vault"),
        ai=ai,
        report=ReportConfig(multi_angle=multi_angle),
        processing=ProcessingConfig(temp_dir="/tmp/test"),
    )


class FakeAIClient:
    def __init__(self, response_json: dict):
        self.response_json = response_json
        self.last_messages = None

    def chat(self, messages: list[dict]) -> str:
        self.last_messages = messages
        return json.dumps(self.response_json, ensure_ascii=False)

    async def chat_async(self, messages: list[dict]) -> str:
        return self.chat(messages)


class MultiResponseFakeClient:
    """Returns different responses by matching a keyword in the system prompt."""

    def __init__(self, responses: dict[str, dict]):
        self.responses = responses
        self.calls: list[str] = []

    def chat(self, messages: list[dict]) -> str:
        system = messages[0]["content"]
        self.calls.append(system)
        for keyword, response in self.responses.items():
            if keyword in system:
                return json.dumps(response, ensure_ascii=False)
        return json.dumps(list(self.responses.values())[0], ensure_ascii=False)

    async def chat_async(self, messages: list[dict]) -> str:
        return self.chat(messages)

    async def aclose(self):
        pass


def test_system_prompt_contains_json_requirements():
    assert "JSON" in SYSTEM_PROMPT
    assert "entities" in SYSTEM_PROMPT
    assert "key_findings" in SYSTEM_PROMPT


def test_generate_report_parses_json_and_renders():
    config = _make_config()
    raw_text = "Paper title: Deep Learning Advances\nAbstract: A test abstract.\nAuthors: John Doe"

    fake_response = {
        "title": "Deep Learning Advances",
        "abstract": "A test abstract.",
        "authors": ["John Doe"],
        "tldr": "提出了Transformer架构，在NLP领域带来突破。",
        "background": "传统序列模型依赖循环或卷积结构，存在并行化困难的问题。",
        "method": "提出基于自注意力机制的Transformer架构，完全摒弃循环结构。",
        "key_findings": [
            "在机器翻译任务上取得了SOTA结果。",
            "训练速度显著优于循环神经网络。",
        ],
        "entities": [
            {"name": "Transformer", "type": "方法", "brief": "基于自注意力的序列模型架构"},
            {"name": "Attention", "type": "概念", "brief": "允许模型关注输入的任意位置"},
        ],
        "keywords": ["deep learning", "transformer", "attention"],
        "references": ["Vaswani et al., 2017", "Brown et al., 2020"],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)

    result = generator.generate_report(raw_text, source_file="test.pdf")
    markdown = result["markdown"]

    assert "A test abstract." in markdown
    assert "[[John Doe]]" in markdown
    assert "[[deep learning]]" in markdown
    assert "[[Transformer]]" in markdown
    assert "（方法）" in markdown
    assert "[[Attention]]" in markdown
    assert "Vaswani et al., 2017" in markdown
    assert "Brown et al., 2020" in markdown
    assert "在机器翻译任务上取得了SOTA结果" in markdown
    assert "提出了Transformer架构" in markdown
    assert "test.pdf" in markdown


def test_generate_report_includes_all_entities():
    config = _make_config()
    raw_text = "A paper about deep learning methods."

    fake_response = {
        "title": "Test",
        "tldr": "...",
        "background": "...",
        "method": "...",
        "key_findings": [],
        "entities": [
            {"name": "CNN", "type": "方法", "brief": "卷积神经网络"},
            {"name": "RNN", "type": "方法", "brief": "循环神经网络"},
            {"name": "Backpropagation", "type": "术语", "brief": "反向传播算法"},
            {"name": "Geoffrey Hinton", "type": "人物", "brief": "深度学习先驱"},
        ],
        "keywords": [],
        "references": [],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)
    result = generator.generate_report(raw_text, source_file="test.pdf")
    markdown = result["markdown"]

    assert "[[CNN]]" in markdown
    assert "[[RNN]]" in markdown
    assert "[[Backpropagation]]" in markdown
    assert "[[Geoffrey Hinton]]" in markdown


def test_prompt_includes_raw_text():
    config = _make_config()
    raw_text = "This is the full paper text.\n\nAbstract: A test abstract.\n\n1. Introduction\nIntroduction text.\n\n2. Method\nMethod description."

    fake_response = {
        "title": "Test",
        "tldr": "...",
        "background": "...",
        "method": "...",
        "key_findings": [],
        "entities": [],
        "keywords": [],
        "references": [],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)
    generator.generate_report(raw_text, source_file="test.pdf")

    user_message = fake_client.last_messages[-1]["content"]
    assert "A test abstract." in user_message
    assert "1. Introduction" in user_message
    assert "Introduction text." in user_message
    assert "2. Method" in user_message
    assert "Method description" in user_message


def test_generate_report_uses_ai_references():
    """In LLM-based extraction, references come from the AI response."""
    config = _make_config()
    raw_text = "A paper about transformers."

    fake_response = {
        "title": "Test",
        "tldr": "...",
        "background": "...",
        "method": "...",
        "key_findings": [],
        "entities": [],
        "keywords": [],
        "references": ["Vaswani et al., 2017", "Brown et al., 2020"],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)
    result = generator.generate_report(raw_text, source_file="test.pdf")
    markdown = result["markdown"]

    assert "Vaswani et al., 2017" in markdown
    assert "Brown et al., 2020" in markdown


def test_generate_report_returns_all_fields():
    """generate_report returns all AI-extracted fields including tldr, background, etc."""
    config = _make_config()
    raw_text = "A test paper."

    fake_response = {
        "title": "My Paper",
        "abstract": "An abstract.",
        "authors": ["Jane Smith"],
        "tldr": "TLDR content",
        "background": "Background content",
        "method": "Method content",
        "key_findings": ["Finding 1", "Finding 2"],
        "entities": [{"name": "Concept", "type": "术语", "brief": "A concept"}],
        "keywords": ["key1", "key2"],
        "references": ["Ref 1"],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)
    result = generator.generate_report(raw_text, source_file="test.pdf")

    assert result["title"] == "My Paper"
    assert result["tldr"] == "TLDR content"
    assert result["background"] == "Background content"
    assert result["method"] == "Method content"
    assert result["key_findings"] == ["Finding 1", "Finding 2"]
    assert len(result["entities"]) == 2  # Concept + author entity
    assert result["references"] == ["Ref 1"]
    assert result["keywords"] == ["key1", "key2"]


def test_fig_table_entities_are_filtered():
    """Figure/Table numbered entities are excluded."""
    config = _make_config()
    raw_text = "A paper about something."

    fake_response = {
        "title": "Test",
        "tldr": "...",
        "background": "...",
        "method": "...",
        "key_findings": [],
        "entities": [
            {"name": "Figure 1", "type": "方法", "brief": "Architecture diagram"},
            {"name": "Table 2", "type": "方法", "brief": "Results table"},
            {"name": "Fig. 3", "type": "概念", "brief": "Something"},
            {"name": "Transformer", "type": "方法", "brief": "A model"},
        ],
        "keywords": [],
        "references": [],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)
    result = generator.generate_report(raw_text, source_file="test.pdf")
    markdown = result["markdown"]

    assert "Figure 1" not in markdown
    assert "Table 2" not in markdown
    assert "Fig. 3" not in markdown
    assert "[[Transformer]]" in markdown


# ---------------------------------------------------------------------------
# Multi-angle analysis tests
# ---------------------------------------------------------------------------


def _make_multi_angle_responses():
    """Build a set of fake responses keyed by a unique keyword in each angle's system prompt."""
    return {
        "文献整理专家": {
            "title": "Deep Learning Advances",
            "authors": ["Jane Smith", "Bob Lee"],
            "abstract": "We propose a novel attention mechanism for sequence modeling.",
            "keywords": ["deep learning", "attention", "transformer"],
            "references": ["Vaswani et al., 2017", "Brown et al., 2020"],
        },
        "评审专家": {
            "problem": "传统序列模型并行化困难，训练效率低",
            "contributions": ["提出高效自注意力机制", "在多项NLP任务达到SOTA"],
            "novelty": "完全摒弃循环结构，使用纯注意力机制",
            "significance": "对NLP和CV领域都有重要影响",
        },
        "技术专家": {
            "approach": "基于自注意力机制的编码器-解码器架构",
            "key_techniques": ["多头注意力", "位置编码", "残差连接", "层归一化"],
            "innovations": "用注意力替代循环结构，实现完全并行化",
            "pipeline": "输入→嵌入→多头注意力→前馈网络→输出",
            "entities": [
                {"name": "Transformer", "type": "方法", "brief": "基于自注意力的序列模型"},
                {"name": "Self-Attention", "type": "概念", "brief": "自注意力机制"},
                {"name": "Positional Encoding", "type": "术语", "brief": "位置编码"},
            ],
        },
        "实验评估专家": {
            "datasets": "WMT 2014 EN-DE (4.5M句对), WMT 2014 EN-FR (36M句对)",
            "baselines": "RNN-based seq2seq, CNN-based seq2seq, ConvS2S",
            "main_results": [
                "EN-DE BLEU达到28.4，超过当时SOTA 2.0分",
                "EN-FR BLEU达到41.8，超过当时SOTA",
                "训练时间仅为RNN模型的1/3",
            ],
            "ablation": "多头注意力头数从8减到1时性能下降约1 BLEU",
            "key_findings": [
                "自注意力机制在序列建模中优于RNN和CNN",
                "多头注意力可以捕获不同类型的依赖关系",
            ],
        },
        "审稿人": {
            "strengths": ["结构简洁优雅", "可并行化程度高"],
            "limitations": ["对长序列的计算复杂度为O(n²)", "缺乏位置归纳偏置"],
            "assumptions": "假设注意力权重可以充分捕获序列中的依赖关系",
            "future_work": "探索更高效的注意力机制，降低长序列的计算复杂度",
        },
        "综述撰写专家": {
            "title": "Deep Learning Advances",
            "authors": ["Jane Smith", "Bob Lee"],
            "abstract": "We propose a novel attention mechanism for sequence modeling.",
            "keywords": ["deep learning", "attention", "transformer"],
            "tldr": "该论文提出了Transformer架构，通过自注意力机制替代循环结构，在机器翻译任务上取得突破性进展。",
            "background": "传统序列建模依赖RNN或CNN，存在并行化困难和长程依赖捕捉不足的问题。",
            "method": "提出基于多头自注意力的Transformer架构，包含编码器和解码器，通过位置编码保留序列信息。",
            "key_findings": [
                "自注意力在序列建模中优于RNN和CNN",
                "训练速度显著提升",
                "在WMT翻译任务上刷新SOTA",
            ],
            "entities": [
                {"name": "Transformer", "type": "方法", "brief": "基于自注意力的序列模型"},
                {"name": "Self-Attention", "type": "概念", "brief": "自注意力机制"},
            ],
            "references": ["Vaswani et al., 2017", "Brown et al., 2020"],
        },
    }


def test_multi_angle_calls_all_angles_and_synthesizer():
    """Multi-angle mode dispatches all 5 angles + 1 synthesizer call."""
    config = _make_config(multi_angle=True)
    raw_text = "Deep Learning Advances\n\nAbstract: We propose a novel attention mechanism."

    responses = _make_multi_angle_responses()
    fake_client = MultiResponseFakeClient(responses)
    generator = ReportGenerator(config, fake_client)

    generator.generate_report(raw_text, source_file="test.pdf", multi_angle=True)

    assert len(fake_client.calls) == 6, f"Expected 6 calls (5 angles + 1 synthesizer), got {len(fake_client.calls)}"

    # Verify each angle was called
    system_texts = "\n".join(fake_client.calls)
    assert "文献整理专家" in system_texts
    assert "评审专家" in system_texts
    assert "技术专家" in system_texts
    assert "实验评估专家" in system_texts
    assert "审稿人" in system_texts
    assert "综述撰写专家" in system_texts


def test_multi_angle_produces_complete_report():
    """Multi-angle report contains all expected sections."""
    config = _make_config(multi_angle=True)
    raw_text = "Deep Learning Advances\n\nAbstract: We propose a novel attention mechanism."

    responses = _make_multi_angle_responses()
    fake_client = MultiResponseFakeClient(responses)
    generator = ReportGenerator(config, fake_client)

    result = generator.generate_report(raw_text, source_file="test.pdf", multi_angle=True)
    markdown = result["markdown"]

    assert "## TL;DR" in markdown
    assert "研究背景" in markdown
    assert "核心方法" in markdown
    assert "关键发现" in markdown
    assert "关键概念" in markdown
    assert "[[Jane Smith]]" in markdown
    assert "[[Bob Lee]]" in markdown
    assert "[[Transformer]]" in markdown
    assert "[[Self-Attention]]" in markdown
    assert "Vaswani et al., 2017" in markdown
    assert "test.pdf" in markdown
    assert result["title"] == "Deep Learning Advances"
    assert len(result["authors"]) == 2
    assert "Jane Smith" in result["authors"]


def test_multi_angle_handles_angle_failure():
    """When an angle fails, synthesis still proceeds with remaining results."""
    config = _make_config(multi_angle=True)
    raw_text = "A paper about something."

    responses = _make_multi_angle_responses()
    # Remove "评审专家" response to simulate a failure in core_contribution angle
    del responses["评审专家"]
    fake_client = MultiResponseFakeClient(responses)
    generator = ReportGenerator(config, fake_client)

    # Should not raise
    result = generator.generate_report(raw_text, source_file="test.pdf", multi_angle=True)

    assert result["title"] == "Deep Learning Advances"
    assert result["markdown"]  # markdown should still be generated


def test_multi_angle_respects_flag_off():
    """When multi_angle=False, uses single-call path (original behavior)."""
    config = _make_config(multi_angle=False)
    raw_text = "A paper about deep learning."

    fake_response = {
        "title": "Test Paper",
        "tldr": "TLDR content.",
        "background": "Background.",
        "method": "Method.",
        "key_findings": ["Finding 1"],
        "entities": [],
        "keywords": [],
        "references": [],
        "abstract": "Abstract.",
        "authors": [],
    }
    fake_client = FakeAIClient(fake_response)
    generator = ReportGenerator(config, fake_client)

    result = generator.generate_report(raw_text, source_file="test.pdf", multi_angle=False)

    assert result["title"] == "Test Paper"
    assert result["tldr"] == "TLDR content."
    # Single call path: only one system prompt = the original SYSTEM_PROMPT
    assert fake_client.last_messages is not None
    assert "学术论文分析助手" in fake_client.last_messages[0]["content"]


def test_multi_angle_entities_deduped():
    """Entities from method analysis and authors are deduplicated."""
    config = _make_config(multi_angle=True)
    raw_text = "A paper."

    responses = _make_multi_angle_responses()
    # Add duplicate entity in synthesizer response to test dedup
    responses["综述撰写专家"]["entities"].append(
        {"name": "Transformer", "type": "方法", "brief": "重复实体"}
    )
    fake_client = MultiResponseFakeClient(responses)
    generator = ReportGenerator(config, fake_client)

    result = generator.generate_report(raw_text, source_file="test.pdf", multi_angle=True)
    markdown = result["markdown"]

    # "Transformer" should appear only once as an entity
    assert markdown.count("[[Transformer]]") == 1
