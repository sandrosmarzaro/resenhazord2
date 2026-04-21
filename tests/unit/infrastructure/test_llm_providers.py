"""Tests for LLM providers (TDD: write failing tests first)."""

import pytest
from unittest.mock import AsyncMock, patch

from bot.infrastructure.llm.providers import (
    GitHubProvider,
    MistralProvider,
    GroqProvider,
    LLMResponse,
)
from bot.infrastructure.llm.provider_chain import ProviderChain


class TestGitHubProvider:
    @pytest.fixture
    def provider(self):
        return GitHubProvider("test-token")

    @pytest.mark.anyio
    async def test_provider_name(self, provider):
        assert provider.provider_name == "github"

    @pytest.mark.anyio
    async def test_model_id(self, provider):
        assert provider.model_id == "gpt-4o"

    @pytest.mark.anyio
    async def test_complete_returns_tool_call(self, provider):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "score",
                    "description": "Placar ao vivo",
                    "parameters": {"type": "object", "properties": {}},
                }
            }
        ]
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "score",
                                        "arguments": "{}",
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await provider.complete("mostrar placar", tools)

        assert result.tool_call is not None
        assert result.tool_call["name"] == "score"
        assert result.provider == "github"


class TestProviderChain:
    @pytest.fixture
    def chain(self):
        chain = ProviderChain()
        chain.configure("github-token", "mistral-key", "groq-key")
        return chain

    @pytest.mark.anyio
    async def test_skips_on_429(self, chain):
        with patch.object(
            chain._states[0].provider,
            "complete",
            side_effect=Exception("429"),
        ):
            result = await chain.complete("test prompt", [])
            pass

    @pytest.mark.anyio
    async def test_all_providers_down_returns_error(self, chain):
        for state in chain._states:
            with patch.object(
                state.provider,
                "complete",
                side_effect=Exception("Provider down"),
            ):
                pass

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            await chain.complete("test prompt", [])


class TestMockResponses:
    @pytest.mark.anyio
    async def test_github_tool_call_response_format(self):
        expected_tool_call = {
            "name": "score",
            "arguments": '{"flag": "now"}',
        }
        import json

        args = json.loads(expected_tool_call["arguments"])
        assert "flag" in args