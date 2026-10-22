from typing import Protocol

from bot.domain.models.llm_response import LLMResponse


class LLMProviderPort(Protocol):
    async def complete(self, prompt: str, tools: list[dict]) -> LLMResponse: ...
