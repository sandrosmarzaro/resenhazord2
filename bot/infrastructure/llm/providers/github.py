from typing import ClassVar

from bot.infrastructure.llm.providers.base import LLMProvider


class GitHubProvider(LLMProvider):
    BASE_URL: ClassVar[str] = 'https://models.github.ai/inference'

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def provider_name(self) -> str:
        return 'github'

    @property
    def model_id(self) -> str:
        return 'gpt-4o'

    def _headers(self) -> dict[str, str]:
        return {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {self._token}',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
        }
