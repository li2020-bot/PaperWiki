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


def _load_backend_config(backend: str, section: dict):
    if backend == "ollama":
        return OllamaConfig(**section)
    else:
        if "api_key" in section:
            section["api_key"] = _interpolate_env(section["api_key"])
        return OpenAICompatConfig(**section)


def load_config(config_path: str = "config.yaml") -> Config:
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    paths = PathsConfig(**raw["paths"])

    ai_raw = raw["ai"]
    backend = ai_raw["backend"]
    ai = AIConfig(backend=backend)

    if backend in ai_raw:
        section = ai_raw[backend].copy()
        setattr(ai, backend, _load_backend_config(backend, section))

    report = ReportConfig(**raw.get("report", {}))
    processing = ProcessingConfig(**raw.get("processing", {}))

    return Config(paths=paths, ai=ai, report=report, processing=processing)
