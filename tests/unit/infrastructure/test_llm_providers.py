"""Tests for LLM providers."""

import httpx
import pytest

from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.providers.base import LLMResponse
from bot.infrastructure.llm.providers.github import GitHubProvider


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

        mock_client.post.assert_called_once()
        call = mock_client.post.call_args
        assert call.args[0] == 'https://models.github.ai/inference/chat/completions'
        assert call.kwargs['json']['model'] == 'gpt-4o'
        assert call.kwargs['json']['messages'] == [{'role': 'user', 'content': 'mostrar placar'}]
        assert call.kwargs['json']['tools'] == tools
        assert call.kwargs['headers']['Authorization'] == 'Bearer test-token'


class TestProviderChain:
    @pytest.fixture
    def chain(self):
        chain = ProviderChain()
        chain.populate('github-token', 'mistral-key', 'groq-key')
        return chain

    @pytest.fixture
    def http_429(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.status_code = 429
        return httpx.HTTPStatusError('429', request=mocker.MagicMock(), response=mock_response)

    @pytest.mark.anyio
    async def test_skips_on_429(self, chain, mocker, http_429):
        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_429)
        mocker.patch.object(chain._states[1].provider, 'complete', side_effect=http_429)
        mocker.patch.object(
            chain._states[2].provider,
            'complete',
            return_value=LLMResponse(content='fallback success', provider='groq', model='mixtral'),
        )

        result = await chain.complete('test prompt', [])

        assert result.content == 'fallback success'
        assert result.provider == 'groq'

    @pytest.mark.anyio
    async def test_subsequent_call_skips_cooldown_provider(self, chain, mocker, http_429):
        github_complete = mocker.patch.object(
            chain._states[0].provider, 'complete', side_effect=http_429
        )
        mistral_complete = mocker.patch.object(
            chain._states[1].provider,
            'complete',
            return_value=LLMResponse(content='ok', provider='mistral', model='small'),
        )

        await chain.complete('first', [])
        github_complete.assert_called_once()
        mistral_complete.assert_called_once()

        await chain.complete('second', [])

        assert github_complete.call_count == 1
        assert mistral_complete.call_count == 2

    @pytest.mark.anyio
    async def test_all_providers_down_returns_error(self, chain, mocker):
        http_error = httpx.HTTPError('Provider down')
        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_error)
        mocker.patch.object(chain._states[1].provider, 'complete', side_effect=http_error)
        mocker.patch.object(chain._states[2].provider, 'complete', side_effect=http_error)

        with pytest.raises(RuntimeError, match='All LLM providers failed'):
            await chain.complete('test prompt', [])


class TestProviderChainConfigure:
    @pytest.fixture
    def chain(self):
        chain = ProviderChain()
        chain.populate('github-token', 'mistral-key', 'groq-key')
        return chain

    def test_configure_sets_instance(self):
        chain = ProviderChain.configure('gh-token', 'mistral-key', 'groq-key')

        assert ProviderChain.instance() is chain

    def test_instance_raises_when_not_configured(self):
        with pytest.raises(RuntimeError, match='not configured'):
            ProviderChain.instance()

    def test_populate_skips_missing_keys(self):
        chain = ProviderChain()
        chain.populate(None, None, None)

        assert chain._states == []

    def test_populate_partial_keys(self):
        chain = ProviderChain()
        chain.populate('gh-token', None, 'groq-key')

        assert len(chain._states) == 2

    @pytest.mark.anyio
    async def test_complete_raises_with_no_providers(self):
        chain = ProviderChain()
        chain.populate(None, None, None)

        with pytest.raises(RuntimeError, match='No LLM providers configured'):
            await chain.complete('test', [])

    @pytest.mark.anyio
    async def test_first_provider_succeeds_immediately(self, chain, mocker):
        mocker.patch.object(
            chain._states[0].provider,
            'complete',
            return_value=LLMResponse(content='first wins', provider='github', model='gpt-4o'),
        )

        result = await chain.complete('test prompt', [])

        assert result.content == 'first wins'
        assert result.provider == 'github'


class TestProviderChainNon429:
    @pytest.mark.anyio
    async def test_non_429_http_error_advances_without_cooldown(self, mocker):
        chain = ProviderChain()
        chain.populate('gh-token', 'mistral-key', None)

        mock_response = mocker.MagicMock()
        mock_response.status_code = 500
        http_500 = httpx.HTTPStatusError('500', request=mocker.MagicMock(), response=mock_response)

        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_500)
        mocker.patch.object(
            chain._states[1].provider,
            'complete',
            return_value=LLMResponse(content='ok', provider='mistral', model='small'),
        )

        result = await chain.complete('test', [])

        assert result.provider == 'mistral'
        assert chain._states[0].cooldown_until == 0.0
