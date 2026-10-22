import pytest

from bot.application.register_commands import register_all_commands
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator
from bot.infrastructure.llm.langchain_provider import LangChainProvider
from bot.infrastructure.llm.langsmith_prompt_registry import LangSmithPromptRegistry
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever
from bot.settings import Settings


class TestAgentWiring:
    def test_always_configures_the_llm_provider_and_graph(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv('REDIS_URL', '')

        agent = register_all_commands(Settings())

        assert LangChainProvider.configured() is not None
        assert agent is GraphAgentOrchestrator.configured()

    def test_optional_services_stay_unconfigured_without_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv('UPSTASH_VECTOR_REST_URL', '')
        monkeypatch.setenv('LANGSMITH_API_KEY', '')

        register_all_commands(Settings())

        assert UpstashExampleRetriever.configured() is None
        assert LangSmithPromptRegistry.configured() is None

    def test_credentials_configure_optional_services(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv('UPSTASH_VECTOR_REST_URL', 'https://example.upstash.io')
        monkeypatch.setenv('UPSTASH_VECTOR_REST_TOKEN', 'token')
        monkeypatch.setenv('LANGSMITH_API_KEY', 'ls-key')

        register_all_commands(Settings())

        assert UpstashExampleRetriever.configured() is not None
        assert LangSmithPromptRegistry.configured() is not None
