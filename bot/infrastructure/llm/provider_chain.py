"""LLM provider chain with fallback and circuit breaker."""

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


class ProviderRateLimitedError(Exception):
    pass


@dataclass
class ProviderState:
    provider: LLMProvider
    cooldown_until: float = 0.0


class ProviderChain:
    RETRY_DELAY: ClassVar[float] = 60.0
    NO_PROVIDERS_MSG: ClassVar[str] = 'No LLM providers configured'
    ALL_FAILED_MSG: ClassVar[str] = 'All LLM providers failed'
    NOT_CONFIGURED_MSG: ClassVar[str] = 'ProviderChain not configured'

    def __init__(self) -> None:
        self._states: list[ProviderState] = []
        self._current_index = 0
        self._lock = asyncio.Lock()

    def configure(
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

    async def complete(
        self,
        prompt: str,
        tools: list[dict],
    ) -> LLMResponse:
        if not self._states:
            raise RuntimeError(self.NO_PROVIDERS_MSG)

        tried = 0

        while tried < len(self._states):
            async with self._lock:
                state = self._states[self._current_index]
                provider = state.provider

                if time.monotonic() < state.cooldown_until:
                    logger.debug('provider_in_cooldown', provider=provider.provider_name)
                    self._advance()
                    tried += 1
                    continue

            logger.info(
                'provider_attempt',
                provider=provider.provider_name,
                model=provider.model_id,
            )

            try:
                response = await provider.complete(prompt, tools)
            except httpx.HTTPStatusError as e:
                logger.warning(
                    'provider_http_error',
                    provider=provider.provider_name,
                    status=e.response.status_code,
                )

                async with self._lock:
                    self._advance()
                    tried += 1

                    if e.response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                        state.cooldown_until = time.monotonic() + self.RETRY_DELAY
                        logger.warning(
                            'provider_rate_limited',
                            provider=provider.provider_name,
                            cooldown=self.RETRY_DELAY,
                        )
            except httpx.HTTPError as e:
                logger.warning(
                    'provider_failed',
                    provider=provider.provider_name,
                    error=str(e),
                )
                async with self._lock:
                    self._advance()
                    tried += 1
            else:
                logger.info(
                    'provider_success',
                    provider=provider.provider_name,
                    has_tool_call=response.tool_call is not None,
                )
                return response

        raise RuntimeError(self.ALL_FAILED_MSG)

    def _advance(self) -> None:
        self._current_index = (self._current_index + 1) % max(len(self._states), 1)


_chain: ProviderChain | None = None


def configure_chain(
    github_token: str | None,
    mistral_key: str | None,
    groq_key: str | None,
) -> ProviderChain:
    # Singleton pattern requires module-level state for get_chain() access
    global _chain  # noqa: PLW0603
    _chain = ProviderChain()
    _chain.configure(github_token, mistral_key, groq_key)
    return _chain


def get_chain() -> ProviderChain:
    if _chain is None:
        raise RuntimeError(ProviderChain.NOT_CONFIGURED_MSG)
    return _chain
