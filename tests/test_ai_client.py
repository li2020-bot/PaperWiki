from paperwiki.config import Config, PathsConfig, AIConfig, ReportConfig, ProcessingConfig
from paperwiki.config import OllamaConfig, OpenAICompatConfig
from paperwiki.ai_client import AIClient


def _make_config(backend="ollama"):
    ai = AIConfig(backend=backend)
    if backend == "ollama":
        ai.ollama = OllamaConfig(base_url="http://localhost:11434", model="qwen3")
    elif backend == "openai":
        ai.openai = OpenAICompatConfig(base_url="https://api.test.com/v1", api_key="sk-test", model="test-model")
    elif backend == "deepseek":
        ai.deepseek = OpenAICompatConfig(base_url="https://api.deepseek.com", api_key="sk-ds", model="deepseek-chat")
    elif backend == "minimax":
        ai.minimax = OpenAICompatConfig(base_url="https://api.minimax.chat/v1", api_key="sk-mm", model="MiniMax-M1")
    elif backend == "qwen":
        ai.qwen = OpenAICompatConfig(base_url="https://dashscope.test.com/v1", api_key="sk-qw", model="qwen-plus")
    elif backend == "custom":
        ai.custom = OpenAICompatConfig(base_url="https://custom.test.com", api_key="sk-cu", model="custom-model")
    return Config(
        paths=PathsConfig(raw_papers="/tmp/papers", obsidian_vault="/tmp/vault"),
        ai=ai,
        report=ReportConfig(),
        processing=ProcessingConfig(temp_dir="/tmp/test"),
    )


def test_ai_client_ollama_backend_selection():
    config = _make_config("ollama")
    client = AIClient(config)
    assert client.backend == "ollama"
    assert client._cfg.model == "qwen3"


def test_ai_client_openai_backend_selection():
    config = _make_config("openai")
    client = AIClient(config)
    assert client.backend == "openai"
    assert client._cfg.base_url == "https://api.test.com/v1"
    assert client._cfg.api_key == "sk-test"


def test_ai_client_deepseek_backend_selection():
    config = _make_config("deepseek")
    client = AIClient(config)
    assert client.backend == "deepseek"
    assert client._cfg.base_url == "https://api.deepseek.com"
    assert client._cfg.model == "deepseek-chat"


def test_ai_client_unknown_backend_raises():
    ai = AIConfig(backend="invalid_backend")
    config = Config(
        paths=PathsConfig(raw_papers="/tmp/papers", obsidian_vault="/tmp/vault"),
        ai=ai,
        report=ReportConfig(),
        processing=ProcessingConfig(),
    )
    try:
        AIClient(config)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
