import httpx
import pytest

from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.providers.base import LLMResponse
from bot.infrastructure.llm.providers.google import GoogleProvider


class TestGoogleProvider:
    @pytest.fixture
    def provider(self):
        GoogleProvider._client = None
        return GoogleProvider('test-token')

    def test_provider_name_and_model(self, provider):
        assert provider.provider_name == 'google'
        assert provider.model_id == 'gemini-3.6-flash'

    @pytest.mark.anyio
    async def test_complete_sends_bearer_auth_and_parses_tool_call(self, provider, respx_mock):
        route = respx_mock.post(f'{GoogleProvider.BASE_URL}/chat/completions').mock(
            return_value=httpx.Response(
                200,
                json={
                    'choices': [
                        {
                            'message': {
                                'tool_calls': [{'function': {'name': 'placar', 'arguments': '{}'}}]
                            }
                        }
                    ]
                },
            )
        )
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'placar',
                    'description': 'Placar ao vivo',
                    'parameters': {'type': 'object', 'properties': {}},
                },
            }
        ]

        result = await provider.complete('mostrar placar', tools)

        assert result.provider == 'google'
        assert result.model == 'gemini-3.6-flash'
        assert result.tool_call == {'name': 'placar', 'arguments': '{}'}
        assert route.calls.last.request.headers['Authorization'] == 'Bearer test-token'


class TestProviderChain:
    @pytest.fixture
    def chain(self):
        chain = ProviderChain()
        chain.populate('mistral-key', 'groq-key', None)
        return chain

    @pytest.fixture
    def http_429(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.status_code = 429
        return httpx.HTTPStatusError('429', request=mocker.MagicMock(), response=mock_response)

    @pytest.mark.anyio
    async def test_falls_back_on_429(self, chain, mocker, http_429):
        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_429)
        mocker.patch.object(
            chain._states[1].provider,
            'complete',
            return_value=LLMResponse(content='fallback success', provider='groq', model='gpt-oss'),
        )

        result = await chain.complete('test prompt', [])

        assert result.content == 'fallback success'
        assert result.provider == 'groq'

    @pytest.mark.anyio
    async def test_subsequent_call_skips_cooldown_provider(self, chain, mocker, http_429):
        mistral_complete = mocker.patch.object(
            chain._states[0].provider, 'complete', side_effect=http_429
        )
        groq_complete = mocker.patch.object(
            chain._states[1].provider,
            'complete',
            return_value=LLMResponse(content='ok', provider='groq', model='gpt-oss'),
        )

        await chain.complete('first', [])
        mistral_complete.assert_called_once()
        groq_complete.assert_called_once()

        await chain.complete('second', [])

        assert mistral_complete.call_count == 1
        assert groq_complete.call_count == 2

    @pytest.mark.anyio
    async def test_all_providers_down_returns_error(self, chain, mocker):
        http_error = httpx.HTTPError('Provider down')
        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_error)
        mocker.patch.object(chain._states[1].provider, 'complete', side_effect=http_error)

        with pytest.raises(RuntimeError, match='All LLM providers failed'):
            await chain.complete('test prompt', [])


class TestProviderChainConfigure:
    def test_configure_sets_instance(self):
        chain = ProviderChain.configure('mistral-key', 'groq-key', 'google-key')

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
        chain.populate(None, 'groq-key', None)

        assert len(chain._states) == 1

    def test_populate_includes_google(self):
        chain = ProviderChain()
        chain.populate('mistral-key', 'groq-key', 'google-key')

        assert len(chain._states) == 3

    @pytest.mark.anyio
    async def test_complete_raises_with_no_providers(self):
        chain = ProviderChain()
        chain.populate(None, None, None)

        with pytest.raises(RuntimeError, match='No LLM providers configured'):
            await chain.complete('test', [])

    @pytest.mark.anyio
    async def test_first_provider_succeeds_immediately(self, mocker):
        chain = ProviderChain()
        chain.populate('mistral-key', 'groq-key', None)
        mocker.patch.object(
            chain._states[0].provider,
            'complete',
            return_value=LLMResponse(content='first wins', provider='mistral', model='small'),
        )

        result = await chain.complete('test prompt', [])

        assert result.content == 'first wins'
        assert result.provider == 'mistral'


class TestProviderChainNon429:
    @pytest.mark.anyio
    async def test_non_429_http_error_advances_without_cooldown(self, mocker):
        chain = ProviderChain()
        chain.populate('mistral-key', 'groq-key', None)

        mock_response = mocker.MagicMock()
        mock_response.status_code = 500
        http_500 = httpx.HTTPStatusError('500', request=mocker.MagicMock(), response=mock_response)

        mocker.patch.object(chain._states[0].provider, 'complete', side_effect=http_500)
        mocker.patch.object(
            chain._states[1].provider,
            'complete',
            return_value=LLMResponse(content='ok', provider='groq', model='gpt-oss'),
        )

        result = await chain.complete('test', [])

        assert result.provider == 'groq'
        assert chain._states[0].cooldown_until == 0
