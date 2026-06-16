import os
import uuid
from dataclasses import replace

import pytest

from bot.domain.constants import CLARIFY_PREFIX
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator

REDIS_URL = os.environ.get('REDIS_URL')

pytestmark = [
    pytest.mark.external,
    pytest.mark.skipif(not REDIS_URL, reason='REDIS_URL absent'),
]


class _ClarifyThenExecute:
    def __init__(self) -> None:
        self.calls: list[CommandData] = []

    async def run(self, data: CommandData) -> CommandData:
        self.calls.append(data)
        if len(self.calls) == 1:
            return replace(data, text=f'{CLARIFY_PREFIX}Qual liga?')
        return replace(data, text=',tabela br')


class TestRedisCheckpointer:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_persists_open_question_across_turns_in_redis(self):
        thread = f'test-{uuid.uuid4()}@g.us'
        executor = _ClarifyThenExecute()
        orchestrator = GraphAgentOrchestrator(executor=executor, redis_url=REDIS_URL)

        first = CommandData(text='tabela', jid=thread, sender_jid='u@x.net')
        second = CommandData(text='a do brasileiro', jid=thread, sender_jid='u@x.net')
        await orchestrator.run(first)
        await orchestrator.run(second)

        assert executor.calls[1].quoted_text == 'Qual liga?'
