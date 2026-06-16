from bot.application.register_commands import register_all_commands
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator
from bot.infrastructure.llm.langchain_provider import LangChainProvider
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever
from bot.settings import Settings


class TestAgentFlagWiring:
    def test_flags_off_leave_agent_singletons_unconfigured(self):
        settings = Settings(_env_file=None)

        register_all_commands(settings)

        assert LangChainProvider.configured() is None
        assert UpstashExampleRetriever.configured() is None
        assert GraphAgentOrchestrator.configured() is None

    def test_flags_on_configure_agent_singletons(self):
        settings = Settings(
            _env_file=None,
            github_token='gh',
            mistral_api_key='mi',
            groq_api_key='gr',
            llm_use_langchain=True,
            upstash_vector_rest_url='https://example.upstash.io',
            upstash_vector_rest_token='token',
            agent_use_graph=True,
        )

        register_all_commands(settings)

        assert LangChainProvider.configured() is not None
        assert UpstashExampleRetriever.configured() is not None
        assert GraphAgentOrchestrator.configured() is not None
