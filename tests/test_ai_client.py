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
