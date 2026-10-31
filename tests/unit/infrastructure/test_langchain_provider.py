import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from bot.infrastructure.llm.langchain_provider import LangChainProvider, _Model


@pytest.fixture
def provider() -> LangChainProvider:
    return LangChainProvider.from_credentials('mistral', 'groq', 'google')


class TestResponseMapping:
    def test_maps_text_content(self, provider):
        response = provider._to_response(AIMessage(content='use ,menu'))

        assert response.content == 'use ,menu'
        assert response.provider == 'langchain'

    def test_maps_tool_call_with_json_encoded_arguments(self, provider):
        message = AIMessage(
            content='',
            tool_calls=[{'name': 'placar', 'args': {'now': True}, 'id': '1', 'type': 'tool_call'}],
        )

        response = provider._to_response(message)

        assert response.tool_call == {'name': 'placar', 'arguments': '{"now": true}'}

    def test_absent_tool_calls_map_to_none(self, provider):
        response = provider._to_response(AIMessage(content='oi'))

        assert response.tool_call is None

    def test_maps_the_reported_token_usage(self, provider):
        usage = {'input_tokens': 7400, 'output_tokens': 60, 'total_tokens': 7460}

        response = provider._to_response(AIMessage(content='oi', usage_metadata=usage))

        assert response.tokens == 7460

    def test_unreported_usage_maps_to_zero_tokens(self, provider):
        response = provider._to_response(AIMessage(content='oi'))

        assert response.tokens == 0


class TestProviderSelection:
    def test_skips_providers_without_credentials(self):
        provider = LangChainProvider.from_credentials('mistral', '', '')

        assert len(provider._models) == 1

    def test_groq_supports_tools(self):
        provider = LangChainProvider.from_credentials('', 'groq', '')

        assert provider._models[0].supports_tools is True

    def test_google_supports_tools(self):
        provider = LangChainProvider.from_credentials('', '', 'google')

        assert provider._models[0].supports_tools is True


class TestComplete:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_returns_the_model_reply(self):
        model = GenericFakeChatModel(messages=iter([AIMessage(content=',menu')]))
        provider = LangChainProvider([_Model(model, supports_tools=False)])

        response = await provider.complete('lista de comandos', [])

        assert response.content == ',menu'

    @pytest.mark.anyio
    async def test_no_credentials_raise_runtime_error_so_the_agent_reports_unavailable(self):
        provider = LangChainProvider.from_credentials('', '', '')

        with pytest.raises(RuntimeError, match='No LLM providers configured'):
            await provider.complete('placar', [])
