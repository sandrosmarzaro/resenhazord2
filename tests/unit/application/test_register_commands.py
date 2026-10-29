import pytest

from bot.application import register_commands
from bot.application.command_registry import CommandRegistry
from bot.application.register_commands import build_agent_graph, register_all_commands
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator
from bot.infrastructure.token_budget import TokenBudgetPolicy
from bot.settings import Settings


@pytest.fixture
def factories(mocker):
    return {
        name: mocker.patch.object(getattr(register_commands, name), 'from_credentials')
        for name in ('LangChainProvider', 'UpstashExampleRetriever', 'LangSmithPromptRegistry')
    }


class TestAgentWiring:
    def test_returns_the_graph_orchestrator(self, monkeypatch: pytest.MonkeyPatch, factories):
        monkeypatch.setenv('REDIS_URL', '')

        agent = register_all_commands(Settings())

        assert isinstance(agent, GraphAgentOrchestrator)

    def test_builds_the_llm_provider_from_the_keys(
        self, monkeypatch: pytest.MonkeyPatch, factories
    ):
        monkeypatch.setenv('MISTRAL_API_KEY', 'mistral')
        monkeypatch.setenv('GROQ_API_KEY', 'groq')
        monkeypatch.setenv('GOOGLE_AI_STUDIO_TOKEN', 'google')

        register_all_commands(Settings())

        factories['LangChainProvider'].assert_called_once_with('mistral', 'groq', 'google')

    def test_optional_services_stay_off_without_credentials(
        self, monkeypatch: pytest.MonkeyPatch, factories
    ):
        monkeypatch.setenv('UPSTASH_VECTOR_REST_URL', '')
        monkeypatch.setenv('LANGSMITH_API_KEY', '')

        register_all_commands(Settings())

        factories['UpstashExampleRetriever'].assert_not_called()
        factories['LangSmithPromptRegistry'].assert_not_called()

    def test_credentials_build_optional_services(self, monkeypatch: pytest.MonkeyPatch, factories):
        monkeypatch.setenv('UPSTASH_VECTOR_REST_URL', 'https://example.upstash.io')
        monkeypatch.setenv('UPSTASH_VECTOR_REST_TOKEN', 'token')
        monkeypatch.setenv('LANGSMITH_API_KEY', 'ls-key')
        monkeypatch.setenv('LANGSMITH_PROMPT_NAME', 'resenhazord-agent')
        monkeypatch.setenv('LANGSMITH_PROMPT_TAG', 'prod')

        register_all_commands(Settings())

        factories['UpstashExampleRetriever'].assert_called_once_with(
            'https://example.upstash.io', 'token'
        )
        factories['LangSmithPromptRegistry'].assert_called_once_with(
            'ls-key', 'resenhazord-agent', 'prod'
        )


class TestTokenBudgetWiring:
    def test_redis_builds_the_budget_from_the_settings(
        self, monkeypatch: pytest.MonkeyPatch, factories, mocker
    ):
        mocker.patch.object(register_commands, 'GraphAgentOrchestrator')
        from_url = mocker.patch.object(register_commands.TokenBudget, 'from_url')
        monkeypatch.setenv('AGENT_TOKENS_PER_DAY_USER', '1000')
        monkeypatch.setenv('AGENT_TOKENS_PER_DAY_GROUP', '5000')
        monkeypatch.setenv('AGENT_BUDGET_ENFORCE', 'true')
        monkeypatch.setenv('OWNER_JIDS', 'owner@s.whatsapp.net, owner@lid')

        build_agent_graph(CommandRegistry.instance(), Settings(), 'redis://localhost')

        policy = TokenBudgetPolicy(
            1000, 5000, enforce=True, owners=frozenset({'owner@s.whatsapp.net', 'owner@lid'})
        )
        from_url.assert_called_once_with('redis://localhost', policy)

    def test_no_redis_means_no_budget(self, factories, mocker):
        mocker.patch.object(register_commands, 'GraphAgentOrchestrator')
        from_url = mocker.patch.object(register_commands.TokenBudget, 'from_url')

        build_agent_graph(CommandRegistry.instance(), Settings(), None)

        from_url.assert_not_called()
