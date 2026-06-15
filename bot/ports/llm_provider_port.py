from typing import Protocol

from bot.infrastructure.llm.providers.base import LLMResponse


class LLMProviderPort(Protocol):
    async def complete(self, prompt: str, tools: list[dict]) -> LLMResponse: ...
