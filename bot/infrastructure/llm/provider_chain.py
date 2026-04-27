import asyncio
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import ClassVar

import httpx
import structlog

from bot.infrastructure.llm.providers.base import LLMProvider, LLMResponse
from bot.infrastructure.llm.providers.github import GitHubProvider
from bot.infrastructure.llm.providers.groq import GroqProvider
from bot.infrastructure.llm.providers.mistral import MistralProvider

logger = structlog.get_logger()


@dataclass
class ProviderState:
    provider: LLMProvider
    cooldown_until: float = 0.0


class ProviderChain:
    RETRY_DELAY: ClassVar[float] = 60.0
    NO_PROVIDERS_MSG: ClassVar[str] = 'No LLM providers configured'
    ALL_FAILED_MSG: ClassVar[str] = 'All LLM providers failed'
    NOT_CONFIGURED_MSG: ClassVar[str] = 'ProviderChain not configured'

    _instance: ClassVar['ProviderChain | None'] = None

    def __init__(self) -> None:
        self._states: list[ProviderState] = []
        self._current_index = 0
        self._lock = asyncio.Lock()

    @classmethod
    def configure(
        cls,
        github_token: str | None,
        mistral_key: str | None,
        groq_key: str | None,
    ) -> 'ProviderChain':
        chain = ProviderChain()
        chain.populate(github_token, mistral_key, groq_key)
        cls._instance = chain
        return chain

    @classmethod
    def instance(cls) -> 'ProviderChain':
        if cls._instance is None:
            raise RuntimeError(cls.NOT_CONFIGURED_MSG)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def populate(
        self,
        github_token: str | None,
        mistral_key: str | None,
        groq_key: str | None,
    ) -> None:
        self._states = []
        if github_token:
            self._states.append(ProviderState(GitHubProvider(github_token)))
        if mistral_key:
            self._states.append(ProviderState(MistralProvider(mistral_key)))
        if groq_key:
            self._states.append(ProviderState(GroqProvider(groq_key)))

    async def complete(self, prompt: str, tools: list[dict]) -> LLMResponse:
        if not self._states:
            raise RuntimeError(self.NO_PROVIDERS_MSG)

        for _ in range(len(self._states)):
            state = await self._next_active_state()
            if state is None:
                continue
            response = await self._invoke(state, prompt, tools)
            if response is not None:
                return response
        raise RuntimeError(self.ALL_FAILED_MSG)

    async def _next_active_state(self) -> ProviderState | None:
        async with self._lock:
            state = self._states[self._current_index]
            if time.monotonic() < state.cooldown_until:
                logger.debug('provider_in_cooldown', provider=state.provider.provider_name)
                self._advance()
                return None
            return state

    async def _invoke(
        self, state: ProviderState, prompt: str, tools: list[dict]
    ) -> LLMResponse | None:
        provider = state.provider
        logger.info('provider_attempt', provider=provider.provider_name, model=provider.model_id)
        try:
            response = await provider.complete(prompt, tools)
        except httpx.HTTPStatusError as error:
            await self._handle_status_error(state, error)
            return None
        except httpx.HTTPError as error:
            await self._handle_transport_error(state, error)
            return None
        logger.info(
            'provider_success',
            provider=provider.provider_name,
            has_tool_call=response.tool_call is not None,
        )
        return response

    async def _handle_status_error(
        self, state: ProviderState, error: httpx.HTTPStatusError
    ) -> None:
        logger.warning(
            'provider_http_error',
            provider=state.provider.provider_name,
            status=error.response.status_code,
        )
        async with self._lock:
            self._advance()
            if error.response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                state.cooldown_until = time.monotonic() + self.RETRY_DELAY
                logger.warning(
                    'provider_rate_limited',
                    provider=state.provider.provider_name,
                    cooldown=self.RETRY_DELAY,
                )

    async def _handle_transport_error(self, state: ProviderState, error: httpx.HTTPError) -> None:
        logger.warning('provider_failed', provider=state.provider.provider_name, error=str(error))
        async with self._lock:
            self._advance()

    def _advance(self) -> None:
        self._current_index = (self._current_index + 1) % max(len(self._states), 1)
