import time
import asyncio
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
        self._async_client = None

    def _get_async_client(self):
        if self._async_client is None:
            from openai import AsyncOpenAI

            self._async_client = AsyncOpenAI(
                base_url=self._cfg.base_url, api_key=self._cfg.api_key
            )
        return self._async_client

    async def aclose(self):
        if self._async_client is not None:
            await self._async_client.close()
            self._async_client = None

    # ---- synchronous ----

    def chat(self, messages: list[dict], max_retries: int = 3) -> str:
        if self.backend == "ollama":
            return self._chat_ollama(messages, max_retries)
        else:
            return self._chat_openai_compat(messages, max_retries)

    # ---- async ----

    async def chat_async(self, messages: list[dict], max_retries: int = 3) -> str:
        if self.backend == "ollama":
            return await self._chat_ollama_async(messages, max_retries)
        else:
            return await self._chat_openai_async(messages, max_retries)

    # ---- ollama ----

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

    async def _chat_ollama_async(self, messages: list[dict], max_retries: int) -> str:
        import ollama

        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    ollama.chat,
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
                await asyncio.sleep(2 ** attempt)

    # ---- openai-compatible ----

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

    async def _chat_openai_async(self, messages: list[dict], max_retries: int) -> str:
        client = self._get_async_client()

        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
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
                await asyncio.sleep(2 ** attempt)
