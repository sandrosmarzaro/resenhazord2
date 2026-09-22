from typing import ClassVar

from bot.infrastructure.llm.providers.base import LLMProvider


class GoogleProvider(LLMProvider):
    # Gemini's OpenAI-compatible surface: same /chat/completions shape as the other
    # providers, so it reuses LLMProvider.complete unchanged.
    BASE_URL: ClassVar[str] = 'https://generativelanguage.googleapis.com/v1beta/openai'

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return 'google'

    @property
    def model_id(self) -> str:
        return 'gemini-3.6-flash'

    def _headers(self) -> dict[str, str]:
        return {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json',
        }
