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
