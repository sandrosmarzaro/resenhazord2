import httpx
import pytest

from bot.application.agent_executor import AgentExecutor
from bot.data.agent_examples import AGENT_EXAMPLES
from bot.domain.constants import (
    CLARIFY_PREFIX,
    SUGGEST_PREFIX,
)
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.langchain_provider import LangChainProvider
from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.providers.base import LLMResponse
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever
from tests.fixtures.fake_example_retriever import FakeExampleRetriever

_STATIC_EXAMPLES = AGENT_EXAMPLES[: AgentExecutor.MAX_AGENT_EXAMPLES]


@pytest.fixture
def executor() -> AgentExecutor:
    return AgentExecutor()


class TestPromptBuilding:
    @pytest.mark.anyio
    async def test_strips_bot_mention(self, executor):
        prompt = executor._build_prompt('@resenhazord ver placar', _STATIC_EXAMPLES)

        assert '@resenhazord' not in prompt
        assert 'ver placar' in prompt

    @pytest.mark.anyio
    async def test_includes_command_list(self, executor):
        prompt = executor._build_prompt('test', _STATIC_EXAMPLES)

        assert 'command_list' in prompt or 'placar' in prompt.lower()

    @pytest.mark.anyio
    async def test_includes_quoted_context_block(self, executor):
        prompt = executor._build_prompt(
            'sim',
            _STATIC_EXAMPLES,
            context='Não sei te dizer..., use ,time',
        )

        assert 'Contexto da mensagem anterior' in prompt
        assert ',time' in prompt

    @pytest.mark.anyio
    async def test_omits_context_block_when_quoted_text_absent(self, executor):
        prompt = executor._build_prompt('me mande um fato', _STATIC_EXAMPLES)

        assert 'Contexto da mensagem anterior' not in prompt


class TestExampleSelection:
    @pytest.mark.anyio
    async def test_returns_static_slice_without_retriever(self, executor):
        examples = await executor._select_examples('qualquer pedido')

        assert examples == list(_STATIC_EXAMPLES)

    def test_defaults_to_configured_singleton(self):
        retriever = UpstashExampleRetriever.configure('https://index.upstash.io', 'token')

        executor = AgentExecutor()

        assert executor._retriever is retriever

    @pytest.mark.anyio
    async def test_uses_retrieved_examples_when_retriever_present(self):
        retriever = FakeExampleRetriever()
        retriever.index('quero ver o placar agora', ',score --now')
        retriever.index('me manda um carro', ',carro')
        executor = AgentExecutor(retriever=retriever)

        examples = await executor._select_examples('@resenhazord placar agora')

        assert examples == [('quero ver o placar agora', ',score --now')]

    @pytest.mark.anyio
    async def test_falls_back_to_static_on_retrieval_error(self, mocker):
        retriever = mocker.Mock()
        retriever.retrieve = mocker.AsyncMock(side_effect=httpx.ConnectError('upstash down'))
        executor = AgentExecutor(retriever=retriever)

        examples = await executor._select_examples('placar agora')

        assert examples == list(_STATIC_EXAMPLES)


class TestRunProviderFailure:
    @pytest.mark.anyio
    async def test_no_providers_returns_clarify_message(self, executor, mocker):
        data = _data('@resenhazord ver placar')
        mock_chain = mocker.Mock()
        mock_chain.complete = mocker.AsyncMock(
            side_effect=RuntimeError('No LLM providers configured'),
        )
        mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)

        result = await executor.run(data)

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'IA indisponível' in result.text
        assert 'menu' in result.text

    @pytest.mark.anyio
    async def test_http_error_returns_clarify_message(self, executor, mocker):
        data = _data('@resenhazord ver placar')
        mock_chain = mocker.Mock()
        mock_chain.complete = mocker.AsyncMock(side_effect=httpx.HTTPError('timeout'))
        mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)

        result = await executor.run(data)

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'IA indisponível' in result.text

    @pytest.mark.anyio
    async def test_unresolvable_content_returns_clarify_message(self, executor, mocker):
        data = _data('@resenhazord blah')
        _stub_chain(mocker, content='random gibberish that matches nothing')

        result = await executor.run(data)

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'menu' in result.text

    @pytest.mark.anyio
    async def test_provider_failure_preserves_media(self, executor, mocker):
        data = CommandData(
            text='@resenhazord blah',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
            media_is_animated=False,
            media_caption='test image',
        )
        mock_chain = mocker.Mock()
        mock_chain.complete = mocker.AsyncMock(
            side_effect=RuntimeError('No LLM providers configured'),
        )
        mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'
        assert result.media_caption == 'test image'

    @pytest.mark.anyio
    async def test_unresolvable_preserves_media(self, executor, mocker):
        data = CommandData(
            text='@resenhazord blah',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
        )
        _stub_chain(mocker, content='random gibberish that matches nothing')

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'


class TestRun:
    @pytest.mark.anyio
    async def test_tool_call_resolves_to_command(self, executor, mocker):
        data = _data('@resenhazord mostrar placar dos jogos')
        _stub_chain(mocker, tool_call={'name': 'placar', 'arguments': '{"now": true}'})

        result = await executor.run(data)

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_preserves_media_fields_on_suggest(self, executor, mocker):
        data = CommandData(
            text='make sticker',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
        )
        _stub_chain(
            mocker,
            tool_call={'name': 'suggest', 'arguments': '{"message": "Use ,carro!"}'},
        )

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'


class TestProviderInjection:
    @pytest.mark.anyio
    async def test_injected_provider_bypasses_provider_chain(self, mocker):
        instance_spy = mocker.patch.object(ProviderChain, 'instance')
        provider = mocker.Mock()
        provider.complete = mocker.AsyncMock(
            return_value=LLMResponse(
                content='',
                provider='x',
                model='m',
                tool_call={'name': 'clarify', 'arguments': '{"question": "confirma?"}'},
            )
        )
        executor = AgentExecutor(provider=provider)

        await executor.run(_data('@resenhazord algo ambíguo'))

        provider.complete.assert_awaited_once()
        instance_spy.assert_not_called()

    def test_defaults_to_configured_langchain_provider(self):
        provider = LangChainProvider.configure('github', '', '')

        executor = AgentExecutor()

        assert executor._provider is provider


class TestToolDecision:
    @pytest.mark.anyio
    async def test_clarify_tool_call_routes_to_clarify(self, executor, mocker):
        _stub_chain(
            mocker,
            tool_call={'name': 'clarify', 'arguments': '{"question": "Qual jogo de cartas?"}'},
        )

        result = await executor.run(_data('@resenhazord uma carta'))

        assert result.text == f'{CLARIFY_PREFIX}Qual jogo de cartas?'

    @pytest.mark.anyio
    async def test_suggest_tool_call_routes_to_suggest(self, executor, mocker):
        _stub_chain(
            mocker,
            tool_call={'name': 'suggest', 'arguments': '{"message": "Use ,time"}'},
        )

        result = await executor.run(_data('@resenhazord fundação do flamengo'))

        assert result.text == f'{SUGGEST_PREFIX}Use ,time'

    @pytest.mark.anyio
    async def test_clarify_tool_call_without_question_falls_back(self, executor, mocker):
        _stub_chain(mocker, tool_call={'name': 'clarify', 'arguments': '{}'})

        result = await executor.run(_data('@resenhazord algo'))

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'menu' in result.text


class TestConfidenceGating:
    @pytest.mark.anyio
    async def test_low_confidence_command_routes_to_confirm(self, executor, mocker):
        _stub_chain(
            mocker,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.3}'},
        )

        result = await executor.run(_data('@resenhazord placar'))

        assert result.text.startswith(CLARIFY_PREFIX)
        assert ',placar now' in result.text

    @pytest.mark.anyio
    async def test_high_confidence_command_executes(self, executor, mocker):
        _stub_chain(
            mocker,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.95}'},
        )

        result = await executor.run(_data('@resenhazord placar'))

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_confidence_is_not_appended_to_the_command(self, executor, mocker):
        _stub_chain(
            mocker,
            tool_call={'name': 'placar', 'arguments': '{"now": true, "confidence": 0.95}'},
        )

        result = await executor.run(_data('@resenhazord placar'))

        assert 'confidence' not in result.text

    @pytest.mark.anyio
    async def test_missing_confidence_defaults_to_execute(self, executor, mocker):
        _stub_chain(mocker, tool_call={'name': 'placar', 'arguments': '{"now": true}'})

        result = await executor.run(_data('@resenhazord placar'))

        assert result.text == ',placar now'


def _data(text: str) -> CommandData:
    return CommandData(text=text, jid='test@g.us', sender_jid='test@s.whatsapp.net')


def _stub_chain(mocker, *, content: str = '', tool_call: dict | None = None) -> None:
    mock_chain = mocker.Mock()
    mock_chain.complete = mocker.AsyncMock(
        return_value=LLMResponse(
            content=content,
            provider='github',
            model='gpt-4o',
            tool_call=tool_call,
        )
    )
    mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)
