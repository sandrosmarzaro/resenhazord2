"""LLM provider implementations with OpenAI-compatible tool calling."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
import structlog

from bot.settings import Settings

logger = structlog.get_logger()

HTTP_STATUS_ERROR_THRESHOLD = 400


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    tool_call: dict | None = None


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        tools: list[dict],
    ) -> LLMResponse: ...

    def _parse_tool_call(self, message: dict) -> dict | None:
        tool_calls = message.get('tool_calls')
        if tool_calls:
            return tool_calls[0]['function']
        return None


class GitHubProvider(LLMProvider):
    BASE_URL = 'https://models.github.ai/inference'

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def provider_name(self) -> str:
        return 'github'

    @property
    def model_id(self) -> str:
        return 'gpt-4o'

    async def complete(
        self,
        prompt: str,
        tools: list[dict],
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            messages = [{'role': 'user', 'content': prompt}]
            payload: dict = {
                'model': self.model_id,
                'messages': messages,
                'max_tokens': 500,
            }
            if tools:
                payload['tools'] = tools

            logger.debug(
                'github_request',
                model=self.model_id,
                has_tools=bool(tools),
                tool_count=len(tools) if tools else 0,
            )
            response = await client.post(
                f'{self.BASE_URL}/chat/completions',
                json=payload,
                headers={
                    'Accept': 'application/vnd.github+json',
                    'Authorization': f'Bearer {self._token}',
                    'X-GitHub-Api-Version': '2022-11-28',
                    'Content-Type': 'application/json',
                },
            )
            if response.status_code >= HTTP_STATUS_ERROR_THRESHOLD:
                logger.warning(
                    'github_error_response',
                    status=response.status_code,
                    body=response.text[:500],
                )
            response.raise_for_status()
            data = response.json()

            choice = data['choices'][0]
            message = choice['message']

            tool_call = self._parse_tool_call(message)

            return LLMResponse(
                content=message.get('content', ''),
                provider=self.provider_name,
                model=self.model_id,
                tool_call=tool_call,
            )


class MistralProvider(LLMProvider):
    BASE_URL = 'https://api.mistral.ai/v1'

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return 'mistral'

    @property
    def model_id(self) -> str:
        return 'mistral-small-latest'

    async def complete(
        self,
        prompt: str,
        tools: list[dict],
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            messages = [{'role': 'user', 'content': prompt}]
            payload: dict = {
                'model': self.model_id,
                'messages': messages,
                'max_tokens': 500,
            }
            if tools:
                payload['tools'] = tools

            response = await client.post(
                f'{self.BASE_URL}/chat/completions',
                json=payload,
                headers={
                    'Authorization': f'Bearer {self._api_key}',
                    'Content-Type': 'application/json',
                },
            )
            response.raise_for_status()
            data = response.json()

            choice = data['choices'][0]
            message = choice['message']

            tool_call = self._parse_tool_call(message)

            return LLMResponse(
                content=message.get('content', ''),
                provider=self.provider_name,
                model=self.model_id,
                tool_call=tool_call,
            )


class GroqProvider(LLMProvider):
    BASE_URL = 'https://api.groq.com/openai/v1'

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return 'groq'

    @property
    def model_id(self) -> str:
        return 'llama-3.3-70b-versatile'

    async def complete(
        self,
        prompt: str,
        tools: list[dict],
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            messages = [{'role': 'user', 'content': prompt}]
            payload: dict = {
                'model': self.model_id,
                'messages': messages,
                'max_tokens': 500,
            }

            # Groq doesn't support tool calling well, use text-based parsing
            response = await client.post(
                f'{self.BASE_URL}/chat/completions',
                json=payload,
                headers={
                    'Authorization': f'Bearer {self._api_key}',
                    'Content-Type': 'application/json',
                },
            )
            response.raise_for_status()
            data = response.json()

            choice = data['choices'][0]
            message = choice['message']

            tool_call = None  # Groq doesn't support tools reliably

            return LLMResponse(
                content=message.get('content', ''),
                provider=self.provider_name,
                model=self.model_id,
                tool_call=tool_call,
            )


def create_provider(settings: Settings) -> LLMProvider | None:
    """Create provider based on settings with fallback order."""
    if settings.github_token:
        return GitHubProvider(settings.github_token)
    if settings.mistral_api_key:
        return MistralProvider(settings.mistral_api_key)
    if settings.groq_api_key:
        return GroqProvider(settings.groq_api_key)
    return None
