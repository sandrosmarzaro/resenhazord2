import pytest

from bot.domain.constants import CLARIFY_PREFIX
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator


def _data(text: str, *, jid: str = 'g@g.us', sender: str = 'u@s.whatsapp.net') -> CommandData:
    return CommandData(text=text, jid=jid, sender_jid=sender)


class TestGraphOrchestrator:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_returns_executor_result(self, mocker):
        executor = mocker.Mock()
        executor.run = mocker.AsyncMock(return_value=_data(',menu'))
        orchestrator = GraphAgentOrchestrator(executor=executor)

        result = await orchestrator.run(_data('@resenhazord comandos'))

        assert result.text == ',menu'

    @pytest.mark.anyio
    async def test_persists_open_question_as_next_turn_context(self, mocker):
        clarify = _data(f'{CLARIFY_PREFIX}Você quer a tabela do brasileiro?')
        executed = _data(',tabela br')
        executor = mocker.Mock()
        executor.run = mocker.AsyncMock(side_effect=[clarify, executed])
        orchestrator = GraphAgentOrchestrator(executor=executor)

        await orchestrator.run(_data('tabela'))
        await orchestrator.run(_data('sim'))

        second_turn_data = executor.run.call_args_list[1].args[0]
        assert second_turn_data.quoted_text == 'Você quer a tabela do brasileiro?'

    @pytest.mark.anyio
    async def test_threads_do_not_share_open_question(self, mocker):
        executor = mocker.Mock()
        executor.run = mocker.AsyncMock(return_value=_data(f'{CLARIFY_PREFIX}pergunta?'))
        orchestrator = GraphAgentOrchestrator(executor=executor)

        await orchestrator.run(_data('algo', jid='g1@g.us'))
        await orchestrator.run(_data('sim', jid='g2@g.us'))

        second_turn_data = executor.run.call_args_list[1].args[0]
        assert second_turn_data.quoted_text is None
