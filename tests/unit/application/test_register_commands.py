import pytest

from bot.application.register_commands import register_all_commands
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator
from bot.infrastructure.llm.langchain_provider import LangChainProvider
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever
from bot.settings import Settings


class TestAgentFlagWiring:
    def test_flags_off_leave_agent_singletons_unconfigured(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv('LLM_USE_LANGCHAIN', 'false')
        monkeypatch.setenv('AGENT_USE_GRAPH', 'false')
        monkeypatch.setenv('UPSTASH_VECTOR_REST_URL', '')

        register_all_commands(Settings())

        assert LangChainProvider.configured() is None
        assert UpstashExampleRetriever.configured() is None
        assert GraphAgentOrchestrator.configured() is None

    def test_flags_on_configure_agent_singletons(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv('LLM_USE_LANGCHAIN', 'true')
        monkeypatch.setenv('AGENT_USE_GRAPH', 'true')
        monkeypatch.setenv('UPSTASH_VECTOR_REST_URL', 'https://example.upstash.io')
        monkeypatch.setenv('UPSTASH_VECTOR_REST_TOKEN', 'token')
        monkeypatch.setenv('GITHUB_TOKEN', 'gh')
        monkeypatch.setenv('REDIS_URL', '')

        register_all_commands(Settings())

        assert LangChainProvider.configured() is not None
        assert UpstashExampleRetriever.configured() is not None
        assert GraphAgentOrchestrator.configured() is not None
