from abc import ABC, abstractmethod
from dataclasses import dataclass
from http import HTTPStatus
from typing import ClassVar

import httpx
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    tool_call: dict | None = None


class LLMProvider(ABC):
    REQUEST_TIMEOUT: ClassVar[float] = 60.0
    MAX_TOKENS: ClassVar[int] = 500
    LOG_BODY_PREVIEW_LENGTH: ClassVar[int] = 500
    SUPPORTS_TOOLS: ClassVar[bool] = True
    BASE_URL: ClassVar[str] = ''

    _client: ClassVar[httpx.AsyncClient | None] = None

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = httpx.AsyncClient(timeout=cls.REQUEST_TIMEOUT)
        return cls._client

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @abstractmethod
    def _headers(self) -> dict[str, str]: ...

    async def complete(self, prompt: str, tools: list[dict]) -> LLMResponse:
        payload: dict = {
            'model': self.model_id,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.MAX_TOKENS,
        }
        if tools and self.SUPPORTS_TOOLS:
            payload['tools'] = tools

        client = self._get_client()
        response = await client.post(
            f'{self.BASE_URL}/chat/completions',
            json=payload,
            headers=self._headers(),
        )
        if response.status_code >= HTTPStatus.BAD_REQUEST:
            logger.warning(
                'llm_error_response',
                provider=self.provider_name,
                status=response.status_code,
                body=response.text[: self.LOG_BODY_PREVIEW_LENGTH],
            )
        response.raise_for_status()

        message = response.json()['choices'][0]['message']
        return LLMResponse(
            content=message.get('content', ''),
            provider=self.provider_name,
            model=self.model_id,
            tool_call=self._parse_tool_call(message) if self.SUPPORTS_TOOLS else None,
        )

    def _parse_tool_call(self, message: dict) -> dict | None:
        tool_calls = message.get('tool_calls')
        if tool_calls:
            return tool_calls[0]['function']
        return None
