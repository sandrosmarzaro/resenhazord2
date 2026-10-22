import httpx
import pytest

from bot.application.agent_executor import AgentExecutor
from bot.application.command_registry import CommandRegistry
from bot.data.agent_examples import AGENT_EXAMPLES
from bot.domain.constants import (
    CLARIFY_PREFIX,
    SUGGEST_PREFIX,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.llm_response import LLMResponse
from bot.domain.models.retrieved_example import RetrievedExample

_STATIC_EXAMPLES = [
    RetrievedExample(text=text, command=command) for text, command in AGENT_EXAMPLES[:5]
]


@pytest.fixture
def provider(mocker):
    provider = mocker.Mock()
    provider.complete = mocker.AsyncMock()
    return provider


@pytest.fixture
def executor(provider) -> AgentExecutor:
    return AgentExecutor(CommandRegistry.instance(), provider)


class TestRunProviderFailure:
    @pytest.mark.anyio
    async def test_no_providers_returns_clarify_message(self, provider, executor, mocker):
        data = _data('@resenhazord ver placar')
        provider.complete.side_effect = RuntimeError('No LLM providers configured')

        result = await executor.run(data)

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'IA indisponível' in result.text
        assert 'menu' in result.text

    @pytest.mark.anyio
    async def test_http_error_returns_clarify_message(self, provider, executor, mocker):
        data = _data('@resenhazord ver placar')
        provider.complete.side_effect = httpx.HTTPError('timeout')

        result = await executor.run(data)

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'IA indisponível' in result.text

    @pytest.mark.anyio
    async def test_unresolvable_content_returns_clarify_message(self, provider, executor, mocker):
        data = _data('@resenhazord blah')
        _stub_provider(provider, content='random gibberish that matches nothing')

        result = await executor.run(data)

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'menu' in result.text

    @pytest.mark.anyio
    async def test_provider_failure_preserves_media(self, provider, executor, mocker):
        data = CommandData(
            text='@resenhazord blah',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
            media_is_animated=False,
            media_caption='test image',
        )
        provider.complete.side_effect = RuntimeError('No LLM providers configured')

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'
        assert result.media_caption == 'test image'

    @pytest.mark.anyio
    async def test_unresolvable_preserves_media(self, provider, executor, mocker):
        data = CommandData(
            text='@resenhazord blah',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
        )
        _stub_provider(provider, content='random gibberish that matches nothing')

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'


class TestRun:
    @pytest.mark.anyio
    async def test_tool_call_resolves_to_command(self, provider, executor, mocker):
        data = _data('@resenhazord mostrar placar dos jogos')
        _stub_provider(provider, tool_call={'name': 'placar', 'arguments': '{"now": true}'})

        result = await executor.run(data)

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_preserves_media_fields_on_suggest(self, provider, executor, mocker):
        data = CommandData(
            text='make sticker',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
        )
        _stub_provider(
            provider,
            tool_call={'name': 'suggest', 'arguments': '{"message": "Use ,carro!"}'},
        )

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'


class TestDirectMatch:
    _IDENTICAL = RetrievedExample(text='time do flamengo', command=',time flamengo', score=0.999)
    _PARAPHRASE = RetrievedExample(text='me mande um carro', command=',carro', score=0.948)

    @staticmethod
    def _executor(mocker, example: RetrievedExample):
        provider = mocker.Mock()
        provider.complete = mocker.AsyncMock(
            return_value=LLMResponse(
                content='', provider='groq', model='m', tool_call={'name': 'carro'}
            )
        )
        executor = AgentExecutor(
            CommandRegistry.instance(), provider, retriever=_scored_retriever(mocker, [example])
        )
        return executor, provider

    @pytest.mark.anyio
    async def test_near_identical_example_runs_without_the_llm(self, mocker):
        executor, llm = self._executor(mocker, self._IDENTICAL)

        result = await executor.run(_data('time do flamengo'))

        assert result.text == ',time flamengo'
        llm.complete.assert_not_awaited()

    @pytest.mark.anyio
    async def test_records_direct_outcome(self, mocker):
        record = mocker.patch('bot.application.agent_executor.record_agent_mapping')
        executor, _ = self._executor(mocker, self._IDENTICAL)

        await executor.run(_data('time do flamengo'))

        record.assert_called_once_with('direct', '', '')

    @pytest.mark.anyio
    async def test_paraphrase_still_goes_to_the_llm(self, mocker):
        executor, llm = self._executor(mocker, self._PARAPHRASE)

        await executor.run(_data('me manda um carro'))

        llm.complete.assert_awaited_once()

    @pytest.mark.anyio
    async def test_reply_to_a_question_never_skips_the_llm(self, mocker):
        executor, llm = self._executor(mocker, self._IDENTICAL)
        data = CommandData(
            text='time do flamengo',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            quoted_text='Quer a tabela ou o time?',
        )

        await executor.run(data)

        llm.complete.assert_awaited_once()


class TestToolDecision:
    @pytest.mark.anyio
    async def test_clarify_tool_call_routes_to_clarify(self, provider, executor, mocker):
        _stub_provider(
            provider,
            tool_call={'name': 'clarify', 'arguments': '{"question": "Qual jogo de cartas?"}'},
        )

        result = await executor.run(_data('@resenhazord uma carta'))

        assert result.text == f'{CLARIFY_PREFIX}Qual jogo de cartas?'

    @pytest.mark.anyio
    async def test_suggest_tool_call_routes_to_suggest(self, provider, executor, mocker):
        _stub_provider(
            provider,
            tool_call={'name': 'suggest', 'arguments': '{"message": "Use ,time"}'},
        )

        result = await executor.run(_data('@resenhazord fundação do flamengo'))

        assert result.text == f'{SUGGEST_PREFIX}Use ,time'

    @pytest.mark.anyio
    async def test_clarify_tool_call_without_question_falls_back(self, provider, executor, mocker):
        _stub_provider(provider, tool_call={'name': 'clarify', 'arguments': '{}'})

        result = await executor.run(_data('@resenhazord algo'))

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'menu' in result.text

    @pytest.mark.anyio
    async def test_suggest_tool_call_without_message_falls_back(self, provider, executor, mocker):
        _stub_provider(provider, tool_call={'name': 'suggest', 'arguments': '{}'})

        result = await executor.run(_data('@resenhazord algo'))

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'menu' in result.text

    @pytest.mark.anyio
    async def test_malformed_tool_arguments_fall_back(self, provider, executor, mocker):
        _stub_provider(provider, tool_call={'name': 'clarify', 'arguments': 'not json'})

        result = await executor.run(_data('@resenhazord algo'))

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'menu' in result.text

    @pytest.mark.anyio
    async def test_plain_text_command_content_executes(self, provider, executor, mocker):
        _stub_provider(provider, content=',menu')

        result = await executor.run(_data('@resenhazord comandos'))

        assert result.text == ',menu'


class TestConfidenceGating:
    @pytest.mark.anyio
    async def test_low_confidence_command_routes_to_confirm(self, provider, executor, mocker):
        _stub_provider(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.3}'},
        )

        result = await executor.run(_data('@resenhazord placar'))

        assert result.text.startswith(CLARIFY_PREFIX)
        assert ',placar now' in result.text

    @pytest.mark.anyio
    async def test_high_confidence_command_executes(self, provider, executor, mocker):
        _stub_provider(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.95}'},
        )

        result = await executor.run(_data('@resenhazord placar'))

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_confidence_is_not_appended_to_the_command(self, provider, executor, mocker):
        _stub_provider(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.95}'},
        )

        result = await executor.run(_data('@resenhazord placar'))

        assert 'confidence' not in result.text

    @pytest.mark.anyio
    async def test_missing_confidence_defaults_to_execute(self, provider, executor, mocker):
        _stub_provider(provider, tool_call={'name': 'placar', 'arguments': '{"now": true}'})

        result = await executor.run(_data('@resenhazord placar'))

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_non_numeric_confidence_defaults_to_execute(self, provider, executor, mocker):
        _stub_provider(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": "alta"}'},
        )

        result = await executor.run(_data('@resenhazord placar'))

        assert result.text == ',placar now'


class TestObservability:
    @pytest.mark.anyio
    async def test_records_command_outcome_with_provider(self, provider, executor, mocker):
        record = mocker.patch('bot.application.agent_executor.record_agent_mapping')
        _stub_provider(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.95}'},
        )

        await executor.run(_data('@resenhazord placar'))

        record.assert_called_once_with('command', 'groq', '')

    @pytest.mark.anyio
    async def test_records_unavailable_outcome_when_provider_fails(
        self, provider, executor, mocker
    ):
        record = mocker.patch('bot.application.agent_executor.record_agent_mapping')
        provider.complete.side_effect = httpx.HTTPError('timeout')

        await executor.run(_data('@resenhazord placar'))

        record.assert_called_once_with('unavailable', '', '')

    @pytest.mark.anyio
    async def test_records_clarify_outcome(self, provider, executor, mocker):
        record = mocker.patch('bot.application.agent_executor.record_agent_mapping')
        _stub_provider(
            provider, tool_call={'name': 'clarify', 'arguments': '{"question": "qual?"}'}
        )

        await executor.run(_data('@resenhazord algo'))

        record.assert_called_once_with('clarify', 'groq', '')

    @pytest.mark.anyio
    async def test_records_suggest_outcome(self, provider, executor, mocker):
        record = mocker.patch('bot.application.agent_executor.record_agent_mapping')
        _stub_provider(
            provider, tool_call={'name': 'suggest', 'arguments': '{"message": "Use ,fato!"}'}
        )

        await executor.run(_data('@resenhazord por que o céu é azul'))

        record.assert_called_once_with('suggest', 'groq', '')

    @pytest.mark.anyio
    async def test_records_confirm_outcome_on_low_confidence(self, provider, executor, mocker):
        record = mocker.patch('bot.application.agent_executor.record_agent_mapping')
        _stub_provider(
            provider,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.2}'},
        )

        await executor.run(_data('@resenhazord placar'))

        record.assert_called_once_with('confirm', 'groq', '')

    @pytest.mark.anyio
    async def test_records_unresolvable_outcome(self, provider, executor, mocker):
        record = mocker.patch('bot.application.agent_executor.record_agent_mapping')
        _stub_provider(provider, content='gibberish that matches nothing')

        await executor.run(_data('@resenhazord blah'))

        record.assert_called_once_with('unresolvable', 'groq', '')


def _data(text: str) -> CommandData:
    return CommandData(text=text, jid='test@g.us', sender_jid='test@s.whatsapp.net')


def _scored_retriever(mocker, examples: list[RetrievedExample]):
    retriever = mocker.Mock()
    retriever.retrieve = mocker.AsyncMock(return_value=examples)
    return retriever


def _stub_provider(provider, *, content: str = '', tool_call: dict | None = None) -> None:
    provider.complete.return_value = LLMResponse(
        content=content,
        provider='groq',
        model='openai/gpt-oss-120b',
        tool_call=tool_call,
    )
