"""LLM provider chain with fallback and circuit breaker."""

import asyncio
from dataclasses import dataclass

import httpx
import structlog

from bot.infrastructure.llm.providers import (
    GitHubProvider,
    GroqProvider,
    LLMProvider,
    LLMResponse,
    MistralProvider,
)

logger = structlog.get_logger()

RETRY_DELAY = 60.0
HTTP_TOO_MANY_REQUESTS = 429
NO_PROVIDERS_MSG = "No LLM providers configured"
ALL_FAILED_MSG = "All LLM providers failed"
NOT_CONFIGURED_MSG = "ProviderChain not configured"


class ProviderRateLimitedError(Exception):
    pass


@dataclass
class ProviderState:
    provider: LLMProvider
    cooldown_until: float = 0.0


class ProviderChain:
    def __init__(self) -> None:
        self._states: list[ProviderState] = []
        self._current_index = 0

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
            raise RuntimeError(NO_PROVIDERS_MSG)

        tried = 0

        while tried < len(self._states):
            state = self._states[self._current_index]
            provider = state.provider

            if asyncio.get_event_loop().time() < state.cooldown_until:
                logger.debug("provider_in_cooldown", provider=provider.provider_name)
                self._advance()
                tried += 1
                continue

            logger.info(
                "provider_attempt",
                provider=provider.provider_name,
                model=provider.model_id,
            )

            try:
                response = await provider.complete(prompt, tools)
                logger.info(
                    "provider_success",
                    provider=provider.provider_name,
                    has_tool_call=response.tool_call is not None,
                )
                return response
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "provider_http_error",
                    provider=provider.provider_name,
                    status=e.response.status_code,
                )

                self._advance()
                tried += 1

                if e.response.status_code == HTTP_TOO_MANY_REQUESTS:
                    state.cooldown_until = asyncio.get_event_loop().time() + RETRY_DELAY
                    logger.warning(
                        "provider_rate_limited",
                        provider=provider.provider_name,
                        cooldown=RETRY_DELAY,
                    )
            except httpx.HTTPError as e:
                logger.warning(
                    "provider_failed",
                    provider=provider.provider_name,
                    error=str(e),
                )
                self._advance()
                tried += 1

        raise RuntimeError(ALL_FAILED_MSG)

    def _advance(self) -> None:
        self._current_index = (self._current_index + 1) % max(len(self._states), 1)


_chain: ProviderChain | None = None


def configure_chain(
    github_token: str | None,
    mistral_key: str | None,
    groq_key: str | None,
) -> ProviderChain:
    global _chain  # noqa: PLW0603 - singleton pattern requires global
    _chain = ProviderChain()
    _chain.configure(github_token, mistral_key, groq_key)
    return _chain


def get_chain() -> ProviderChain:
    if _chain is None:
        raise RuntimeError(NOT_CONFIGURED_MSG)
    return _chain
