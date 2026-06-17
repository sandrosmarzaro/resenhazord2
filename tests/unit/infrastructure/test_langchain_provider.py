import pytest
from langchain_core.messages import AIMessage

from bot.infrastructure.llm.langchain_provider import LangChainProvider


@pytest.fixture
def provider() -> LangChainProvider:
    return LangChainProvider.from_credentials('github', 'mistral', 'groq')


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


class TestProviderSelection:
    def test_skips_providers_without_credentials(self):
        provider = LangChainProvider.from_credentials('github', '', '')

        assert len(provider._models) == 1

    def test_groq_is_text_only(self):
        provider = LangChainProvider.from_credentials('', '', 'groq')

        assert provider._models[0].supports_tools is False
