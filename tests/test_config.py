import os
import tempfile
from paperwiki.config import load_config


def test_load_config_basic():
    yaml_content = """
paths:
  raw_papers: ~/papers
  obsidian_vault: ~/vault
  wiki_subdir: wiki
ai:
  backend: ollama
  ollama:
    base_url: http://localhost:11434
    model: qwen3
report:
  multi_angle: false
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
        assert config.ai.backend == "ollama"
        assert config.ai.ollama.base_url == "http://localhost:11434"
        assert config.ai.ollama.model == "qwen3"
        assert config.report.multi_angle is False
    finally:
        os.unlink(tmp_path)


def test_load_config_env_var_interpolation():
    os.environ["TEST_API_KEY"] = "sk-test-123"
    try:
        yaml_content = """
paths:
  raw_papers: ~/papers
  obsidian_vault: ~/vault
  wiki_subdir: wiki
ai:
  backend: openai
  openai:
    base_url: https://api.openai.com/v1
    api_key: ${TEST_API_KEY}
    model: gpt-4o
report:
  multi_angle: false
processing:
  temp_dir: /tmp/test
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            config = load_config(tmp_path)
            assert config.ai.openai.api_key == "sk-test-123"
            assert config.report.multi_angle is False
        finally:
            os.unlink(tmp_path)
    finally:
        del os.environ["TEST_API_KEY"]


def test_expand_tilde():
    from paperwiki.config import _expand_path
    path = _expand_path("~/Documents/test")
    assert path.startswith(os.path.expanduser("~"))
    assert not path.startswith("~")
