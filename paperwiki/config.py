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
        env_val = os.environ.get(name)
        if env_val is None:
            raise KeyError(
                f"Environment variable '{name}' referenced in config is not set"
            )
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
