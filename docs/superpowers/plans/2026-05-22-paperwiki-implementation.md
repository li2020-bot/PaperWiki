# PaperWiki Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS tool that monitors a folder for PDF papers, extracts text, analyzes them via AI (Ollama or cloud API), and generates Obsidian-compatible Markdown learning reports with wiki links.

**Architecture:** Modular Python pipeline — 6 modules (config, pdf_extractor, ai_client, report_generator, obsidian_writer, main) with test coverage per module. TDD approach: write failing test first, then implement.

**Tech Stack:** Python 3.10+, PyMuPDF, watchdog, ollama, openai, PyYAML, Jinja2, pytest

---

### Task 1: Project skeleton

**Files:**
- Create: `requirements.txt`
- Create: `paperwiki/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
watchdog>=4.0.0
PyMuPDF>=1.24.0
ollama>=0.3.0
openai>=1.30.0
PyYAML>=6.0
Jinja2>=3.1.0
pytest>=8.0.0
```

- [ ] **Step 2: Create paperwiki/__init__.py**

```python
"""PaperWiki - AI-powered PDF-to-Obsidian learning report generator."""
```

- [ ] **Step 3: Create tests/__init__.py**

```python
"""Tests for PaperWiki."""
```

- [ ] **Step 4: Install dependencies**

Run: `pip install -r requirements.txt`

---

### Task 2: Config module

**Files:**
- Create: `paperwiki/config.py`
- Create: `tests/test_config.py`
- Create: `config.yaml`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
import os
import tempfile
from paperwiki.config import load_config


def test_load_config_basic():
    yaml_content = """
paths:
  raw_papers: ~/papers
  obsidian_vault: ~/vault
  wiki_subdir: wiki
  raw_subdir: raw
ai:
  backend: ollama
  ollama:
    base_url: http://localhost:11434
    model: qwen3
report:
  language: zh-CN
processing:
  temp_dir: /tmp/test
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        config = load_config(tmp_path)
        assert config.paths.raw_papers.endswith("papers")
        assert config.paths.obsidian_vault.endswith("vault")
        assert config.paths.wiki_subdir == "wiki"
        assert config.paths.raw_subdir == "raw"
        assert config.ai.backend == "ollama"
        assert config.ai.ollama.base_url == "http://localhost:11434"
        assert config.ai.ollama.model == "qwen3"
    finally:
        os.unlink(tmp_path)


def test_load_config_env_var_interpolation():
    os.environ["TEST_API_KEY"] = "sk-test-123"
    yaml_content = """
paths:
  raw_papers: ~/papers
  obsidian_vault: ~/vault
  wiki_subdir: wiki
  raw_subdir: raw
ai:
  backend: openai
  openai:
    base_url: https://api.openai.com/v1
    api_key: ${TEST_API_KEY}
    model: gpt-4o
report:
  language: zh-CN
processing:
  temp_dir: /tmp/test
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        config = load_config(tmp_path)
        assert config.ai.openai.api_key == "sk-test-123"
    finally:
        os.unlink(tmp_path)


def test_expand_tilde():
    from paperwiki.config import _expand_path
    path = _expand_path("~/Documents/test")
    assert path.startswith(os.path.expanduser("~"))
    assert not path.startswith("~")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — module not found or import errors

- [ ] **Step 3: Create config.yaml template**

`config.yaml`:
```yaml
paths:
  raw_papers: ~/Documents/raw_papers
  obsidian_vault: ~/Documents/ObsidianVault
  wiki_subdir: wiki
  raw_subdir: raw

ai:
  backend: ollama              # ollama | openai | deepseek | minimax | qwen | custom
  ollama:
    base_url: http://localhost:11434
    model: qwen3
  openai:
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    model: gpt-4o
  deepseek:
    base_url: https://api.deepseek.com
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat
  minimax:
    base_url: https://api.minimax.chat/v1
    api_key: ${MINIMAX_API_KEY}
    model: MiniMax-M1
  qwen:
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key: ${QWEN_API_KEY}
    model: qwen-plus
  custom:
    base_url: https://your-api-endpoint
    api_key: ${CUSTOM_API_KEY}
    model: your-model-name

report:
  language: zh-CN

processing:
  temp_dir: /tmp/paperwiki
```

- [ ] **Step 4: Write minimal implementation**

`paperwiki/config.py`:
```python
import os
import re
import yaml
from dataclasses import dataclass, field


def _expand_path(path: str) -> str:
    if path.startswith("~"):
        return os.path.expanduser(path)
    return path


def _interpolate_env(value: str) -> str:
    pattern = re.compile(r"\$\{(\w+)\}")
    matches = pattern.findall(value)
    for name in matches:
        env_val = os.environ.get(name, "")
        value = value.replace(f"${{{name}}}", env_val)
    return value


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "qwen3"


@dataclass
class OpenAICompatConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = ""


@dataclass
class AIConfig:
    backend: str = "ollama"
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAICompatConfig = field(default_factory=OpenAICompatConfig)
    deepseek: OpenAICompatConfig = field(default_factory=OpenAICompatConfig)
    minimax: OpenAICompatConfig = field(default_factory=OpenAICompatConfig)
    qwen: OpenAICompatConfig = field(default_factory=OpenAICompatConfig)
    custom: OpenAICompatConfig = field(default_factory=OpenAICompatConfig)


@dataclass
class PathsConfig:
    raw_papers: str = ""
    obsidian_vault: str = ""
    wiki_subdir: str = "wiki"
    raw_subdir: str = "raw"

    def __post_init__(self):
        self.raw_papers = _expand_path(self.raw_papers)
        self.obsidian_vault = _expand_path(self.obsidian_vault)


@dataclass
class ReportConfig:
    language: str = "zh-CN"


@dataclass
class ProcessingConfig:
    temp_dir: str = "/tmp/paperwiki"

    def __post_init__(self):
        self.temp_dir = _expand_path(self.temp_dir)


@dataclass
class Config:
    paths: PathsConfig
    ai: AIConfig
    report: ReportConfig
    processing: ProcessingConfig


def load_config(config_path: str = "config.yaml") -> Config:
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    paths = PathsConfig(**raw["paths"])

    ai_raw = raw["ai"]
    ai = AIConfig(backend=ai_raw["backend"])
    for key in ("ollama", "openai", "deepseek", "minimax", "qwen", "custom"):
        if key in ai_raw:
            section = ai_raw[key].copy()
            if "api_key" in section:
                section["api_key"] = _interpolate_env(section["api_key"])
            if key == "ollama":
                setattr(ai, key, OllamaConfig(**section))
            else:
                setattr(ai, key, OpenAICompatConfig(**section))

    report = ReportConfig(**raw.get("report", {}))
    processing = ProcessingConfig(**raw.get("processing", {}))

    return Config(paths=paths, ai=ai, report=report, processing=processing)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt paperwiki/__init__.py tests/__init__.py paperwiki/config.py tests/test_config.py config.yaml
git commit -m "feat: add config module with YAML parsing and env var interpolation"
```

---

### Task 3: PDF extractor module

**Files:**
- Create: `paperwiki/pdf_extractor.py`
- Create: `tests/test_pdf_extractor.py`

- [ ] **Step 1: Write the failing test**

`tests/test_pdf_extractor.py`:
```python
import os
import tempfile
import fitz
from paperwiki.pdf_extractor import extract_text


def _create_test_pdf(text: str) -> str:
    """Create a temporary PDF with given text for testing."""
    doc = fitz.open()
    doc.new_page()
    page = doc[0]
    page.insert_text((72, 72), text, fontsize=12)
    doc.set_metadata({"title": "Test Paper", "author": "Test Author"})
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    doc.save(tmp.name)
    doc.close()
    return tmp.name


def test_extract_text_basic():
    pdf_path = _create_test_pdf("This is a test paper about machine learning.")
    try:
        text, metadata = extract_text(pdf_path)
        assert "test paper" in text.lower()
        assert "machine learning" in text.lower()
        assert metadata["title"] == "Test Paper"
        assert metadata["author"] == "Test Author"
    finally:
        os.unlink(pdf_path)


def test_extract_text_multi_page():
    doc = fitz.open()
    for _ in range(3):
        doc.new_page()
        doc[-1].insert_text((72, 72), "Page content", fontsize=12)
    doc.set_metadata({"title": "Multi Page", "author": ""})
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    doc.save(tmp.name)
    doc.close()

    try:
        text, metadata = extract_text(tmp.name)
        assert text.count("Page content") == 3
        assert metadata["title"] == "Multi Page"
    finally:
        os.unlink(tmp.name)


def test_extract_text_empty_pdf():
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({"title": "", "author": ""})
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    doc.save(tmp.name)
    doc.close()

    try:
        text, metadata = extract_text(tmp.name)
        assert isinstance(text, str)
        assert isinstance(metadata, dict)
    finally:
        os.unlink(tmp.name)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pdf_extractor.py -v`
Expected: FAIL — module not found or function not defined

- [ ] **Step 3: Write minimal implementation**

`paperwiki/pdf_extractor.py`:
```python
import fitz


def extract_text(pdf_path: str) -> tuple:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())

    text = "\n".join(pages)
    meta = doc.metadata or {}
    metadata = {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
    }
    doc.close()
    return text, metadata
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pdf_extractor.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add paperwiki/pdf_extractor.py tests/test_pdf_extractor.py
git commit -m "feat: add PDF extractor module using PyMuPDF"
```

---

### Task 4: AI client module

**Files:**
- Create: `paperwiki/ai_client.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Write the failing test**

`tests/test_ai_client.py`:
```python
import os
from paperwiki.config import Config, PathsConfig, AIConfig, ReportConfig, ProcessingConfig
from paperwiki.config import OllamaConfig, OpenAICompatConfig
from paperwiki.ai_client import AIClient


def _make_config(backend="ollama"):
    ai = AIConfig(backend=backend)
    ai.ollama = OllamaConfig(base_url="http://localhost:11434", model="qwen3")
    ai.openai = OpenAICompatConfig(base_url="https://api.test.com/v1", api_key="sk-test", model="test-model")
    ai.deepseek = OpenAICompatConfig(base_url="https://api.deepseek.com", api_key="sk-ds", model="deepseek-chat")
    ai.minimax = OpenAICompatConfig(base_url="https://api.minimax.chat/v1", api_key="sk-mm", model="MiniMax-M1")
    ai.qwen = OpenAICompatConfig(base_url="https://dashscope.test.com/v1", api_key="sk-qw", model="qwen-plus")
    ai.custom = OpenAICompatConfig(base_url="https://custom.test.com", api_key="sk-cu", model="custom-model")
    return Config(
        paths=PathsConfig(raw_papers="/tmp/papers", obsidian_vault="/tmp/vault"),
        ai=ai,
        report=ReportConfig(language="zh-CN"),
        processing=ProcessingConfig(temp_dir="/tmp/test"),
    )


def test_ai_client_ollama_backend_selection():
    config = _make_config("ollama")
    client = AIClient(config)
    assert client.backend == "ollama"


def test_ai_client_openai_backend_selection():
    config = _make_config("openai")
    client = AIClient(config)
    assert client.backend == "openai"


def test_ai_client_get_backend_config_ollama():
    config = _make_config("ollama")
    client = AIClient(config)
    backend_cfg = client._get_backend_config()
    assert backend_cfg["base_url"] == "http://localhost:11434"
    assert backend_cfg["model"] == "qwen3"


def test_ai_client_get_backend_config_openai():
    config = _make_config("openai")
    client = AIClient(config)
    backend_cfg = client._get_backend_config()
    assert backend_cfg["base_url"] == "https://api.test.com/v1"
    assert backend_cfg["api_key"] == "sk-test"


def test_ai_client_get_backend_config_deepseek():
    config = _make_config("deepseek")
    client = AIClient(config)
    backend_cfg = client._get_backend_config()
    assert backend_cfg["base_url"] == "https://api.deepseek.com"
    assert backend_cfg["model"] == "deepseek-chat"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_client.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

`paperwiki/ai_client.py`:
```python
import re
import time
from paperwiki.config import Config


class AIClient:
    def __init__(self, config: Config):
        self.config = config
        self.backend = config.ai.backend

    def _get_backend_config(self) -> dict:
        section = getattr(self.config.ai, self.backend, None)
        if section is None:
            raise ValueError(f"Unknown AI backend: {self.backend}")
        return {
            "base_url": section.base_url,
            "api_key": getattr(section, "api_key", ""),
            "model": section.model,
        }

    def chat(self, messages: list[dict], max_retries: int = 3) -> str:
        if self.backend == "ollama":
            return self._chat_ollama(messages, max_retries)
        else:
            return self._chat_openai_compat(messages, max_retries)

    def _chat_ollama(self, messages: list[dict], max_retries: int) -> str:
        import ollama
        cfg = self._get_backend_config()

        for attempt in range(max_retries):
            try:
                response = ollama.chat(
                    model=cfg["model"],
                    messages=messages,
                    options={"temperature": 0.3},
                )
                return response["message"]["content"]
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

    def _chat_openai_compat(self, messages: list[dict], max_retries: int) -> str:
        from openai import OpenAI
        cfg = self._get_backend_config()

        client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=cfg["model"],
                    messages=messages,
                    temperature=0.3,
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ai_client.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add paperwiki/ai_client.py tests/test_ai_client.py
git commit -m "feat: add AI client with multi-backend support (Ollama + OpenAI-compatible)"
```

---

### Task 5: Report generator module

**Files:**
- Create: `paperwiki/report_generator.py`
- Create: `tests/test_report_generator.py`

- [ ] **Step 1: Write the failing test**

`tests/test_report_generator.py`:
```python
import json
from datetime import datetime
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_report_generator.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

`paperwiki/report_generator.py`:
```python
import json
import re
from datetime import datetime
from jinja2 import Template
from paperwiki.config import Config


SYSTEM_PROMPT = """你是一个学术论文分析助手。根据提供的论文文本，生成一份JSON格式的分析报告。
JSON必须包含以下字段：
- title: 论文标题
- summary: 300字以内的中文摘要
- entities: 数组，每项含 name(名称) 和 type(类型，取值为: 人物/术语/概念/方法)
- references: 数组，重要参考文献列表

只返回JSON，不要包含其他文字。"""

REPORT_TEMPLATE = """# {{ title }}

## 摘要
{{ summary }}

## 关键实体
{% for entity in entities %}
- [[{{ entity.name }}]] ({{ entity.type }})
{% endfor %}

## 参考文献
{% for ref in references %}
- {{ ref }}
{% endfor %}

## 原始文本
- [[raw/{{ title }}|查看原始提取文本]]

---
*自动生成于 {{ generated_at }} | 来源: {{ source_file }}*"""


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)


class ReportGenerator:
    def __init__(self, config: Config, ai_client):
        self.config = config
        self.ai_client = ai_client
        self.template = Template(REPORT_TEMPLATE)

    def _call_ai(self, paper_text: str) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": paper_text},
        ]
        response = self.ai_client.chat(messages)
        return json.loads(self._extract_json(response))

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text

    def generate_report(self, paper_text: str, metadata: dict, source_file: str) -> str:
        ai_result = self._call_ai(paper_text)

        title = ai_result.get("title", metadata.get("title", "Untitled"))
        summary = ai_result.get("summary", "")
        entities = ai_result.get("entities", [])
        references = ai_result.get("references", [])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        markdown = self.template.render(
            title=title,
            summary=summary,
            entities=entities,
            references=references,
            generated_at=now,
            source_file=source_file,
        )
        return markdown

    @property
    def output_filename(self) -> str:
        return None  # Will be set after generation
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_report_generator.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add paperwiki/report_generator.py tests/test_report_generator.py
git commit -m "feat: add report generator with Jinja2 template and JSON prompt"
```

---

### Task 6: Obsidian writer module

**Files:**
- Create: `paperwiki/obsidian_writer.py`
- Create: `tests/test_obsidian_writer.py`

- [ ] **Step 1: Write the failing test**

`tests/test_obsidian_writer.py`:
```python
import os
import json
import tempfile
import hashlib
from paperwiki.obsidian_writer import ObsidianWriter


def test_sanitize_filename():
    w = ObsidianWriter("/tmp/vault", "wiki", "raw")
    assert w._sanitize_filename("Deep Learning: A Survey") == "Deep Learning_ A Survey"
    assert w._sanitize_filename("a/b:c*d?e\"f<g>h|i") == "a_b_c_d_e_f_g_h_i"


def test_save_report_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        writer = ObsidianWriter(vault, "wiki", "raw")
        writer.save_report(
            report_markdown="# Test Report\nContent here.",
            title="Test Paper Title",
            source_file="/tmp/test.pdf",
        )

        expected_dir = os.path.join(vault, "wiki")
        expected_file = os.path.join(expected_dir, "Test Paper Title.md")
        assert os.path.exists(expected_file)

        with open(expected_file, "r") as f:
            content = f.read()
        assert "# Test Report" in content
        assert "Content here." in content


def test_save_raw_text_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        writer = ObsidianWriter(vault, "wiki", "raw")
        writer.save_raw_text(
            raw_text="Raw paper text content.",
            title="Test Paper Title",
            source_file="/tmp/test.pdf",
        )

        expected_dir = os.path.join(vault, "wiki", "raw")
        expected_file = os.path.join(expected_dir, "Test Paper Title.md")
        assert os.path.exists(expected_file)

        with open(expected_file, "r") as f:
            content = f.read()
        assert "Raw paper text content." in content
        assert "# Test Paper Title" in content


def test_processed_files_tracking():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        processed_path = os.path.join(tmp, "processed.json")
        writer = ObsidianWriter(vault, "wiki", "raw", processed_path)

        writer.save_report("# Report", "Paper One", "/tmp/paper1.pdf")

        with open(processed_path, "r") as f:
            data = json.load(f)
        assert "/tmp/paper1.pdf" in data
        assert "hash" in data["/tmp/paper1.pdf"]
        assert data["/tmp/paper1.pdf"]["output_file"] == "Paper One.md"


def test_is_processed():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        processed_path = os.path.join(tmp, "processed.json")
        writer = ObsidianWriter(vault, "wiki", "raw", processed_path)

        assert not writer.is_processed("/tmp/nonexistent.pdf")

        writer.save_report("# Report", "Paper Test", "/tmp/paper.pdf")
        assert writer.is_processed("/tmp/paper.pdf")


def test_hash_calculation():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"test pdf content 123")
        tmp_path = f.name

    try:
        h1 = ObsidianWriter._file_hash(tmp_path)
        h2 = ObsidianWriter._file_hash(tmp_path)
        assert h1 == h2
        assert isinstance(h1, str)
        assert len(h1) == 64
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_obsidian_writer.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

`paperwiki/obsidian_writer.py`:
```python
import os
import re
import json
import hashlib
from datetime import datetime


class ObsidianWriter:
    def __init__(self, obsidian_vault: str, wiki_subdir: str, raw_subdir: str,
                 processed_path: str = "processed_files.json"):
        self.vault = obsidian_vault
        self.wiki_dir = os.path.join(obsidian_vault, wiki_subdir)
        self.raw_dir = os.path.join(self.wiki_dir, raw_subdir)
        self.processed_path = processed_path
        self._ensure_dirs()
        self._processed = self._load_processed()

    def _ensure_dirs(self):
        os.makedirs(self.wiki_dir, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)

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
            with open(self.processed_path, "r") as f:
                return json.load(f)
        return {}

    def _save_processed(self):
        with open(self.processed_path, "w") as f:
            json.dump(self._processed, f, indent=2, ensure_ascii=False)

    def is_processed(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        file_hash = self._file_hash(filepath)
        if filepath in self._processed:
            return self._processed[filepath]["hash"] == file_hash
        return False

    def _mark_processed(self, filepath: str, output_file: str):
        self._processed[filepath] = {
            "hash": self._file_hash(filepath),
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

    def save_raw_text(self, raw_text: str, title: str, source_file: str):
        filename = self._sanitize_filename(title) + ".md"
        filepath = os.path.join(self.raw_dir, filename)
        content = f"# {title}\n\n{raw_text}\n\n---\n*原始提取文本 | 来源: {os.path.basename(source_file)}*"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_obsidian_writer.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add paperwiki/obsidian_writer.py tests/test_obsidian_writer.py
git commit -m "feat: add obsidian writer with report/raw-text saving and dedup tracking"
```

---

### Task 7: Main entry point and watchdog integration

**Files:**
- Create: `paperwiki/main.py`

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
import os
import tempfile
import time
import shutil
from paperwiki.main import process_pdf


class FakeAIClient:
    def chat(self, messages):
        import json
        return json.dumps({
            "title": "Test Paper",
            "summary": "A test summary.",
            "entities": [{"name": "Test Entity", "type": "概念"}],
            "references": ["Test Ref, 2026"],
        })


class FakeConfig:
    class Paths:
        def __init__(self, raw_papers, obsidian_vault, wiki_subdir, raw_subdir):
            self.raw_papers = raw_papers
            self.obsidian_vault = obsidian_vault
            self.wiki_subdir = wiki_subdir
            self.raw_subdir = raw_subdir

    class AI:
        backend = "ollama"

    class Report:
        language = "zh-CN"

    class Processing:
        temp_dir = "/tmp/paperwiki_test"

    def __init__(self, raw_papers, obsidian_vault):
        self.paths = self.Paths(raw_papers, obsidian_vault, "wiki", "raw")
        self.ai = self.AI()
        self.report = self.Report()
        self.processing = self.Processing()


def _create_test_pdf(dir_path: str, filename: str, text: str):
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc[0].insert_text((72, 72), text, fontsize=12)
    doc.set_metadata({"title": "Test Paper", "author": "Test Author"})
    pdf_path = os.path.join(dir_path, filename)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_process_pdf_creates_report_and_raw():
    with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as vault_dir:
        config = FakeConfig(raw_dir, vault_dir)
        pdf_path = _create_test_pdf(raw_dir, "test_paper.pdf", "Paper content for testing.")

        fake_ai = FakeAIClient()
        process_pdf(pdf_path, config, ai_client=fake_ai)

        report_path = os.path.join(vault_dir, "wiki", "Test Paper.md")
        raw_path = os.path.join(vault_dir, "wiki", "raw", "Test Paper.md")

        assert os.path.exists(report_path), f"Report not found at {report_path}"
        assert os.path.exists(raw_path), f"Raw text not found at {raw_path}"

        with open(report_path, "r") as f:
            report = f.read()
        assert "Test Paper" in report
        assert "Test Entity" in report
        assert "[[Test Entity]]" in report

        with open(raw_path, "r") as f:
            raw = f.read()
        assert "Paper content for testing." in raw


def test_process_pdf_skips_already_processed():
    with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as vault_dir:
        config = FakeConfig(raw_dir, vault_dir)
        pdf_path = _create_test_pdf(raw_dir, "test.pdf", "Content.")

        fake_ai = FakeAIClient()
        result1 = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result1 is True

        result2 = process_pdf(pdf_path, config, ai_client=fake_ai)
        assert result2 is False or result2 is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

`paperwiki/main.py`:
```python
import os
import sys
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

ERROR_LOG = "error.log"


def _log_error(message: str):
    with open(ERROR_LOG, "a") as f:
        f.write(message + "\n")
    logger.error(message)


def process_pdf(pdf_path: str, config, ai_client=None) -> bool:
    if not pdf_path.lower().endswith(".pdf"):
        return False

    ai = ai_client or AIClient(config)
    writer = ObsidianWriter(
        config.paths.obsidian_vault,
        config.paths.wiki_subdir,
        config.paths.raw_subdir,
    )

    if writer.is_processed(pdf_path):
        logger.info(f"Skipping already processed: {pdf_path}")
        return False

    logger.info(f"Processing: {pdf_path}")

    try:
        text, metadata = extract_text(pdf_path)
    except Exception as e:
        _log_error(f"PDF extraction failed for {pdf_path}: {e}")
        return False

    try:
        generator = ReportGenerator(config, ai)
        report = generator.generate_report(text, metadata, source_file=pdf_path)
    except Exception as e:
        _log_error(f"AI report generation failed for {pdf_path}: {e}")
        return False

    try:
        title = metadata.get("title") or "Untitled"
        writer.save_report(report, title, pdf_path)
        writer.save_raw_text(text, title, pdf_path)
    except Exception as e:
        _log_error(f"Failed to write output for {pdf_path}: {e}")
        return False

    logger.info(f"Completed: {pdf_path}")
    return True


def main():
    config = load_config()

    os.makedirs(config.paths.raw_papers, exist_ok=True)
    os.makedirs(config.paths.obsidian_vault, exist_ok=True)
    os.makedirs(config.processing.temp_dir, exist_ok=True)

    logger.info(f"Watching: {config.paths.raw_papers}")
    logger.info(f"Output: {config.paths.obsidian_vault}/{config.paths.wiki_subdir}")
    logger.info(f"AI Backend: {config.ai.backend}")

    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class PDFHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            process_pdf(event.src_path, config)

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add paperwiki/main.py tests/test_main.py
git commit -m "feat: add main entry point with watchdog file monitoring and pipeline orchestration"
```

---

### Task 8: End-to-end integration test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write the integration test**

`tests/test_integration.py`:
```python
import os
import json
import tempfile
import time
import shutil
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
        processed_path = os.path.join(os.getcwd(), "processed_files.json")

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

        if os.path.exists(processed_path):
            os.unlink(processed_path)


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

        processed_path = os.path.join(os.getcwd(), "processed_files.json")
        if os.path.exists(processed_path):
            os.unlink(processed_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_integration.py -v`
Expected: FAIL (or PASS if implementation exists)

- [ ] **Step 3: Run integration tests to verify all PASS**

Run: `python -m pytest tests/test_integration.py -v`
Expected: 2 PASS

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (3 + 3 + 5 + 4 + 6 + 2 + 2 = ~25 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests for full pipeline"
```

---

### Task 9: Run entry script and verify project completeness

- [ ] **Step 1: Verify project structure**

Run: `find . -type f -name "*.py" -o -name "*.yaml" -o -name "*.txt" | sort`
Expected: All modules, tests, and config files listed

- [ ] **Step 2: Python syntax check on all modules**

Run: `python -m py_compile paperwiki/config.py && python -m py_compile paperwiki/pdf_extractor.py && python -m py_compile paperwiki/ai_client.py && python -m py_compile paperwiki/report_generator.py && python -m py_compile paperwiki/obsidian_writer.py && python -m py_compile paperwiki/main.py`
Expected: No output (all compile clean)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: finalize project structure and verify completeness"
```
