import os
import uuid

import pytest

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.application.example_selector import ExampleSelector
from bot.application.llm_command_mapper import LLMCommandMapper
from bot.domain.models.command_data import CommandData
from bot.domain.models.llm_response import LLMResponse
from bot.infrastructure.llm.agent_graph_nodes import AgentGraphNodes
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator

REDIS_URL = os.environ.get('REDIS_URL')

pytestmark = [
    pytest.mark.external,
    pytest.mark.skipif(not REDIS_URL, reason='REDIS_URL absent'),
]


class _UnsureProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, prompt: str, tools: list[dict]) -> LLMResponse:
        self.calls += 1
        arguments = '{"now": true, "confidence": 0.3}'
        return LLMResponse(
            content='',
            provider='groq',
            model='m',
            tool_call={'name': 'placar', 'arguments': arguments},
        )


class TestRedisCheckpointer:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_confirmation_survives_a_round_trip_through_redis(self):
        thread = f'test-{uuid.uuid4()}@g.us'
        provider = _UnsureProvider()
        registry = CommandRegistry.instance()
        nodes = AgentGraphNodes(
            ExampleSelector(None),
            LLMCommandMapper(registry, provider),
            AgentResponseTranslator(registry),
        )
        orchestrator = GraphAgentOrchestrator(nodes, REDIS_URL)

        await orchestrator.run(CommandData(text='placar', jid=thread, sender_jid='u@x.net'))
        result = await orchestrator.run(CommandData(text='sim', jid=thread, sender_jid='u@x.net'))

        assert result.text == ',placar now'
        assert provider.calls == 1
