import time
import logging
from paperwiki.config import Config

logger = logging.getLogger("paperwiki.ai_client")

VALID_BACKENDS = ("ollama", "openai", "deepseek", "minimax", "qwen", "custom")


class AIClient:
    def __init__(self, config: Config):
        self.backend = config.ai.backend
        if self.backend not in VALID_BACKENDS:
            raise ValueError(f"Unknown AI backend: {self.backend}")
        self._cfg = getattr(config.ai, self.backend, None)
        if self._cfg is None:
            raise ValueError(f"No config found for backend: {self.backend}")

    def chat(self, messages: list[dict], max_retries: int = 3) -> str:
        if self.backend == "ollama":
            return self._chat_ollama(messages, max_retries)
        else:
            return self._chat_openai_compat(messages, max_retries)

    def _chat_ollama(self, messages: list[dict], max_retries: int) -> str:
        import ollama

        for attempt in range(max_retries):
            try:
                response = ollama.chat(
                    model=self._cfg.model,
                    messages=messages,
                    options={"temperature": 0.3},
                )
                return response["message"]["content"]
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    "Ollama chat attempt %d/%d failed: %s. Retrying in %ds...",
                    attempt + 1, max_retries, e, 2 ** attempt,
                )
                time.sleep(2 ** attempt)

    def _chat_openai_compat(self, messages: list[dict], max_retries: int) -> str:
        from openai import OpenAI

        client = OpenAI(base_url=self._cfg.base_url, api_key=self._cfg.api_key)

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self._cfg.model,
                    messages=messages,
                    temperature=0.3,
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    "%s chat attempt %d/%d failed: %s. Retrying in %ds...",
                    self.backend, attempt + 1, max_retries, e, 2 ** attempt,
                )
                time.sleep(2 ** attempt)
