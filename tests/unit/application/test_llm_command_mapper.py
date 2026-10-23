import httpx
import pytest

from bot.application.command_registry import CommandRegistry
from bot.application.llm_command_mapper import LLMCommandMapper
from bot.domain.models.agent_decision import AgentDecision, AgentOutcome
from bot.domain.models.command_data import CommandData
from bot.domain.models.llm_response import LLMResponse
from bot.domain.models.retrieved_example import RetrievedExample
from bot.domain.models.system_prompt import SystemPrompt
from bot.ports.prompt_registry_port import PromptRegistryError

_EXAMPLE = RetrievedExample(text='mostrar placar dos jogos', command=',score --now', score=0.9)


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def provider(mocker):
    provider = mocker.Mock()
    provider.complete = mocker.AsyncMock(
        return_value=LLMResponse(content='', provider='groq', model='m')
    )
    return provider


@pytest.fixture
def mapper(provider) -> LLMCommandMapper:
    return LLMCommandMapper(CommandRegistry.instance(), provider)


def _reply(provider, *, content: str = '', tool_call: dict | None = None) -> None:
    provider.complete.return_value = LLMResponse(
        content=content, provider='groq', model='m', tool_call=tool_call
    )


def _data(text: str, *, quoted_text: str | None = None) -> CommandData:
    return CommandData(
        text=text, jid='test@g.us', sender_jid='test@s.whatsapp.net', quoted_text=quoted_text
    )


def _prompt(provider) -> str:
    return provider.complete.call_args.args[0]


class _FakePromptRegistry:
    def __init__(self, system_prompt: SystemPrompt) -> None:
        self._system_prompt = system_prompt

    def system_prompt(self) -> SystemPrompt:
        return self._system_prompt


class TestPrompt:
    @pytest.mark.anyio
    async def test_strips_the_bot_mention(self, mapper, provider):
        await mapper.map(_data('@resenhazord ver placar'), [_EXAMPLE])

        assert '@resenhazord' not in _prompt(provider)
        assert 'ver placar' in _prompt(provider)

    @pytest.mark.anyio
    async def test_includes_the_examples(self, mapper, provider):
        await mapper.map(_data('placar'), [_EXAMPLE])

        assert 'Usuário: "mostrar placar dos jogos" -> Comando: ,score --now' in _prompt(provider)

    @pytest.mark.anyio
    async def test_includes_the_quoted_question_as_context(self, mapper, provider):
        await mapper.map(_data('sim', quoted_text='Não sei..., use ,time'), [])

        assert 'Contexto da mensagem anterior: "Não sei..., use ,time"' in _prompt(provider)

    @pytest.mark.anyio
    async def test_omits_the_context_block_without_a_quote(self, mapper, provider):
        await mapper.map(_data('me mande um fato'), [])

        assert 'Contexto da mensagem anterior' not in _prompt(provider)

    @pytest.mark.anyio
    async def test_uses_the_registry_prompt_and_reports_its_version(self, provider):
        injected = SystemPrompt(template='CUSTOM {command_list}', version='abc123')
        mapper = LLMCommandMapper(
            CommandRegistry.instance(), provider, _FakePromptRegistry(injected)
        )

        decision = await mapper.map(_data('placar'), [])

        assert _prompt(provider).startswith('CUSTOM')
        assert decision.prompt_version == 'abc123'


class TestToolCalls:
    @pytest.mark.anyio
    async def test_command_tool_call_maps_to_the_command(self, mapper, provider):
        _reply(provider, tool_call={'name': 'placar', 'arguments': '{"now": true}'})

        decision = await mapper.map(_data('placar agora'), [])

        assert decision == AgentDecision(
            AgentOutcome.COMMAND, command=',placar now', provider='groq'
        )

    @pytest.mark.anyio
    async def test_low_confidence_command_asks_for_confirmation(self, mapper, provider):
        _reply(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.3}'},
        )

        decision = await mapper.map(_data('placar'), [])

        assert decision.outcome == AgentOutcome.CONFIRM
        assert decision.command == ',placar now'
        assert decision.text == 'Você quis dizer `,placar now`?'

    @pytest.mark.anyio
    async def test_non_numeric_confidence_executes(self, mapper, provider):
        _reply(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": "alta"}'},
        )

        decision = await mapper.map(_data('placar'), [])

        assert decision.outcome == AgentOutcome.COMMAND

    @pytest.mark.anyio
    async def test_clarify_carries_the_question(self, mapper, provider):
        _reply(
            provider,
            tool_call={'name': 'clarify', 'arguments': '{"question": "Qual jogo de cartas?"}'},
        )

        decision = await mapper.map(_data('uma carta'), [])

        assert decision.outcome == AgentOutcome.CLARIFY
        assert decision.text == 'Qual jogo de cartas?'

    @pytest.mark.anyio
    async def test_suggest_carries_the_message(self, mapper, provider):
        _reply(provider, tool_call={'name': 'suggest', 'arguments': '{"message": "Use ,time"}'})

        decision = await mapper.map(_data('fundação do flamengo'), [])

        assert decision.outcome == AgentOutcome.SUGGEST
        assert decision.text == 'Use ,time'

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'tool_call',
        [
            {'name': 'clarify', 'arguments': '{}'},
            {'name': 'suggest', 'arguments': '{}'},
            {'name': 'clarify', 'arguments': 'not json'},
        ],
    )
    async def test_empty_or_malformed_meta_tool_is_unresolvable(self, mapper, provider, tool_call):
        _reply(provider, tool_call=tool_call)

        decision = await mapper.map(_data('algo'), [])

        assert decision.outcome == AgentOutcome.UNRESOLVABLE
        assert 'menu' in decision.text


class TestPlainContent:
    @pytest.mark.anyio
    async def test_command_text_maps_to_the_command(self, mapper, provider):
        _reply(provider, content=',menu')

        decision = await mapper.map(_data('comandos'), [])

        assert decision.outcome == AgentOutcome.COMMAND
        assert decision.command == ',menu'

    @pytest.mark.anyio
    async def test_free_text_is_unresolvable(self, mapper, provider):
        _reply(provider, content='random gibberish that matches nothing')

        decision = await mapper.map(_data('blah'), [])

        assert decision.outcome == AgentOutcome.UNRESOLVABLE


class TestProviderFailure:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'error',
        [
            RuntimeError('No LLM providers configured'),
            httpx.HTTPError('timeout'),
            PromptRegistryError('hub down'),
        ],
    )
    async def test_failure_is_unavailable(self, mapper, provider, error):
        provider.complete.side_effect = error

        decision = await mapper.map(_data('placar'), [])

        assert decision.outcome == AgentOutcome.UNAVAILABLE
        assert 'IA indisponível' in decision.text

    @pytest.mark.anyio
    async def test_failure_alerts_sentry(self, mapper, provider, mocker):
        capture = mocker.patch('bot.application.llm_command_mapper.sentry_sdk.capture_message')
        provider.complete.side_effect = httpx.HTTPError('rate limited')

        await mapper.map(_data('placar'), [])

        capture.assert_called_once_with('agent_unavailable', level='error')
