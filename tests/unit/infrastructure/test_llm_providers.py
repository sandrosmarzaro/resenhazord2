"""Tests for LLM providers."""

import httpx
import pytest

from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.providers import (
    GitHubProvider,
    LLMResponse,
)


class TestGitHubProvider:
    @pytest.fixture
    def provider(self):
        return GitHubProvider('test-token')

    @pytest.mark.anyio
    async def test_provider_name(self, provider):
        assert provider.provider_name == 'github'

    @pytest.mark.anyio
    async def test_model_id(self, provider):
        assert provider.model_id == 'gpt-4o'

    @pytest.mark.anyio
    async def test_complete_returns_tool_call(self, provider, mocker):
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'score',
                    'description': 'Placar ao vivo',
                    'parameters': {'type': 'object', 'properties': {}},
                },
            }
        ]
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.text = ''
        mock_response.raise_for_status = mocker.MagicMock()
        mock_response.json = mocker.MagicMock(
            return_value={
                'choices': [
                    {
                        'message': {
                            'tool_calls': [
                                {
                                    'function': {
                                        'name': 'score',
                                        'arguments': '{}',
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )

        mock_client = mocker.MagicMock()
        mock_client.post = mocker.AsyncMock(return_value=mock_response)
        mocker.patch.object(GitHubProvider, '_client', mock_client)

        result = await provider.complete('mostrar placar', tools)

        assert result.tool_call is not None
        assert result.tool_call['name'] == 'score'
        assert result.provider == 'github'


class TestProviderChain:
    @pytest.fixture
    def chain(self):
        chain = ProviderChain()
        chain.configure('github-token', 'mistral-key', 'groq-key')
        return chain

    @pytest.mark.anyio
    async def test_skips_on_429(self, chain, mocker):
        mock_response = mocker.MagicMock()
        mock_response.status_code = 429
        http_error = httpx.HTTPStatusError('429', request=mocker.MagicMock(), response=mock_response)

        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_error)
        mocker.patch.object(chain._states[1].provider, 'complete', side_effect=http_error)
        mocker.patch.object(
            chain._states[2].provider,
            'complete',
            return_value=LLMResponse(content='fallback success', provider='groq', model='mixtral'),
        )

        result = await chain.complete('test prompt', [])

        assert result.content == 'fallback success'
        assert result.provider == 'groq'

    @pytest.mark.anyio
    async def test_all_providers_down_returns_error(self, chain, mocker):
        http_error = httpx.HTTPError('Provider down')
        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_error)
        mocker.patch.object(chain._states[1].provider, 'complete', side_effect=http_error)
        mocker.patch.object(chain._states[2].provider, 'complete', side_effect=http_error)

        with pytest.raises(RuntimeError, match='All LLM providers failed'):
            await chain.complete('test prompt', [])
