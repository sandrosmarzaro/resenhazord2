from typing import ClassVar

from bot.infrastructure.llm.providers.base import LLMProvider


class GroqProvider(LLMProvider):
    BASE_URL: ClassVar[str] = 'https://api.groq.com/openai/v1'

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return 'groq'

    @property
    def model_id(self) -> str:
        return 'openai/gpt-oss-120b'

    def _headers(self) -> dict[str, str]:
        return {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json',
        }
