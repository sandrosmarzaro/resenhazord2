import pytest

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.application.example_selector import ExampleSelector
from bot.application.llm_command_mapper import LLMCommandMapper
from bot.domain.constants import CLARIFY_PREFIX, SUGGEST_PREFIX
from bot.domain.models.command_data import CommandData
from bot.domain.models.conversation import Conversation
from bot.domain.models.llm_response import LLMResponse
from bot.domain.models.retrieved_example import RetrievedExample
from bot.infrastructure.llm.agent_graph_nodes import AgentGraphNodes
from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator

_NODES_MODULE = 'bot.infrastructure.llm.agent_graph_nodes'
_PROPOSAL = 'Você quis dizer `,placar now`?'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def provider(mocker):
    provider = mocker.Mock()
    provider.complete = mocker.AsyncMock()
    return provider


@pytest.fixture
def clock(mocker):
    clock = mocker.patch(f'{_NODES_MODULE}.time.time')
    clock.return_value = 1000.0
    return clock


def _orchestrator(provider, *, retriever=None, redis_url: str | None = None):
    registry = CommandRegistry.instance()
    nodes = AgentGraphNodes(
        ExampleSelector(retriever),
        LLMCommandMapper(registry, provider),
        AgentResponseTranslator(registry),
    )
    return GraphAgentOrchestrator(nodes, redis_url)


def _replies(provider, *responses: LLMResponse) -> None:
    provider.complete.side_effect = list(responses)


def _tool(name: str, arguments: str) -> LLMResponse:
    return LLMResponse(
        content='', provider='groq', model='m', tool_call={'name': name, 'arguments': arguments}
    )


def _command(confidence: float = 0.95) -> LLMResponse:
    return _tool('placar', f'{{"now": true, "confidence": {confidence}}}')


def _clarify(question: str = 'Qual liga?') -> LLMResponse:
    return _tool('clarify', f'{{"question": "{question}"}}')


def _data(text: str, *, jid: str = 'g@g.us', quoted_text: str | None = None) -> CommandData:
    return CommandData(
        text=text, jid=jid, sender_jid='u@s.whatsapp.net', is_group=True, quoted_text=quoted_text
    )


def _prompt(provider, call: int) -> str:
    return provider.complete.call_args_list[call].args[0]


class TestCommand:
    @pytest.mark.anyio
    async def test_confident_command_executes(self, provider, clock):
        _replies(provider, _command())

        result = await _orchestrator(provider).run(_data('placar agora'))

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_near_identical_example_executes_without_the_llm(self, provider, clock, mocker):
        retriever = mocker.Mock()
        retriever.retrieve = mocker.AsyncMock(
            return_value=[RetrievedExample('time do flamengo', ',time flamengo', 0.999)]
        )

        result = await _orchestrator(provider, retriever=retriever).run(_data('time do flamengo'))

        assert result.text == ',time flamengo'
        provider.complete.assert_not_awaited()

    @pytest.mark.anyio
    async def test_execution_records_the_outcome_and_provider(self, provider, clock, mocker):
        record = mocker.patch(f'{_NODES_MODULE}.record_agent_mapping')
        _replies(provider, _command())

        await _orchestrator(provider).run(_data('placar agora'))

        record.assert_called_once_with('command', 'groq', '')


class TestConfirmation:
    @pytest.mark.anyio
    async def test_unsure_command_asks_for_confirmation(self, provider, clock):
        _replies(provider, _command(confidence=0.3))

        result = await _orchestrator(provider).run(_data('placar'))

        assert result.text == f'{CLARIFY_PREFIX}{_PROPOSAL}'

    @pytest.mark.anyio
    async def test_yes_runs_the_proposed_command_without_the_llm(self, provider, clock):
        _replies(provider, _command(confidence=0.3))
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('placar'))

        result = await orchestrator.run(_data('Sim!'))

        assert result.text == ',placar now'
        provider.complete.assert_awaited_once()

    @pytest.mark.anyio
    async def test_yes_is_recorded_as_confirmed(self, provider, clock, mocker):
        record = mocker.patch(f'{_NODES_MODULE}.record_agent_mapping')
        _replies(provider, _command(confidence=0.3))
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('placar'))

        await orchestrator.run(_data('sim'))

        assert record.call_args.args[0] == 'confirmed'

    @pytest.mark.anyio
    async def test_no_asks_what_was_wanted_without_the_llm(self, provider, clock):
        _replies(provider, _command(confidence=0.3))
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('placar'))

        result = await orchestrator.run(_data('não'))

        assert result.text == f'{CLARIFY_PREFIX}O que você queria?'
        provider.complete.assert_awaited_once()

    @pytest.mark.anyio
    async def test_other_reply_is_a_new_request_with_the_proposal_as_context(self, provider, clock):
        _replies(provider, _command(confidence=0.3), _command())
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('placar'))

        await orchestrator.run(_data('na verdade a tabela'))

        assert f'Contexto da mensagem anterior: "{_PROPOSAL}"' in _prompt(provider, 1)


class TestClarification:
    @pytest.mark.anyio
    async def test_question_becomes_the_next_turn_context(self, provider, clock):
        _replies(provider, _clarify(), _command())
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('tabela'))

        await orchestrator.run(_data('a do brasileiro'))

        assert 'Contexto da mensagem anterior: "Qual liga?"' in _prompt(provider, 1)

    @pytest.mark.anyio
    async def test_third_clarification_gives_the_menu_hint(self, provider, clock):
        _replies(provider, _clarify(), _clarify(), _clarify())
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('algo'))
        await orchestrator.run(_data('outra coisa'))

        result = await orchestrator.run(_data('mais uma'))

        assert result.text == f'{CLARIFY_PREFIX}{LLMCommandMapper.UNRESOLVABLE_MSG}'

    @pytest.mark.anyio
    async def test_no_counts_as_an_attempt(self, provider, clock):
        _replies(provider, _command(confidence=0.3), _clarify(), _clarify())
        orchestrator = _orchestrator(provider)
        for text in ('placar', 'não', 'sei la'):
            await orchestrator.run(_data(text))

        result = await orchestrator.run(_data('hmm'))

        assert result.text == f'{CLARIFY_PREFIX}{LLMCommandMapper.UNRESOLVABLE_MSG}'

    @pytest.mark.anyio
    async def test_executing_resets_the_attempts(self, provider, clock):
        _replies(provider, _clarify(), _command(), _clarify(), _clarify('De qual time?'))
        orchestrator = _orchestrator(provider)
        for text in ('algo', 'placar', 'outra'):
            await orchestrator.run(_data(text))

        result = await orchestrator.run(_data('mais'))

        assert result.text == f'{CLARIFY_PREFIX}De qual time?'

    @pytest.mark.anyio
    async def test_waiting_for_an_answer_skips_the_direct_match(self, provider, clock, mocker):
        retriever = mocker.Mock()
        retriever.retrieve = mocker.AsyncMock(
            side_effect=[[], [RetrievedExample('time do flamengo', ',time flamengo', 0.999)]]
        )
        _replies(provider, _clarify('Time ou tabela?'), _command())
        orchestrator = _orchestrator(provider, retriever=retriever)
        await orchestrator.run(_data('flamengo'))

        await orchestrator.run(_data('time do flamengo'))

        assert provider.complete.await_count == 2


class TestOpenEndedReplies:
    @pytest.mark.anyio
    async def test_suggestion_leaves_nothing_pending(self, provider, clock):
        _replies(provider, _tool('suggest', '{"message": "Use ,time"}'), _command())
        orchestrator = _orchestrator(provider)
        first = await orchestrator.run(_data('fundação do flamengo'))

        await orchestrator.run(_data('sim'))

        assert first.text == f'{SUGGEST_PREFIX}Use ,time'
        assert 'Contexto da mensagem anterior' not in _prompt(provider, 1)

    @pytest.mark.anyio
    async def test_provider_failure_replies_unavailable(self, provider, clock):
        provider.complete.side_effect = RuntimeError('No LLM providers configured')

        result = await _orchestrator(provider).run(_data('placar'))

        assert result.text == f'{CLARIFY_PREFIX}{LLMCommandMapper.UNAVAILABLE_MSG}'

    @pytest.mark.anyio
    async def test_reply_keeps_the_media(self, provider, clock):
        provider.complete.side_effect = RuntimeError('No LLM providers configured')
        data = CommandData(
            text='faz uma figurinha',
            jid='g@g.us',
            sender_jid='u@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
        )

        result = await _orchestrator(provider).run(data)

        assert (result.media_type, result.media_source) == (
            'image',
            'https://example.com/image.jpg',
        )


class TestConversationScope:
    @pytest.mark.anyio
    async def test_pending_confirmation_expires(self, provider, clock):
        _replies(provider, _command(confidence=0.3), _command())
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('placar'))
        clock.return_value = 1000.0 + Conversation.RESUME_WINDOW_SECONDS + 1

        await orchestrator.run(_data('sim'))

        assert provider.complete.await_count == 2
        assert 'Contexto da mensagem anterior' not in _prompt(provider, 1)

    @pytest.mark.anyio
    async def test_chats_do_not_share_pending_state(self, provider, clock):
        _replies(provider, _command(confidence=0.3), _command())
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('placar', jid='a@g.us'))

        await orchestrator.run(_data('sim', jid='b@g.us'))

        assert provider.complete.await_count == 2

    @pytest.mark.anyio
    async def test_quote_takes_precedence_over_the_pending_question(self, provider, clock):
        _replies(provider, _clarify('pergunta persistida?'), _command())
        orchestrator = _orchestrator(provider)
        await orchestrator.run(_data('algo'))

        await orchestrator.run(_data('isso', quoted_text='citação do usuário'))

        assert 'Contexto da mensagem anterior: "citação do usuário"' in _prompt(provider, 1)


class TestUnreachableCheckpointer:
    @pytest.mark.anyio
    async def test_still_answers_without_conversation_memory(self, provider, clock):
        _replies(provider, _command())
        orchestrator = _orchestrator(provider, redis_url='redis://127.0.0.1:1')

        result = await orchestrator.run(_data('placar agora'))

        assert result.text == ',placar now'
