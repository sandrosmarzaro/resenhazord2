import pytest

from bot.application.agent_executor import AgentExecutor
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.providers.base import LLMResponse


@pytest.fixture
def executor() -> AgentExecutor:
    return AgentExecutor()


class TestPromptBuilding:
    @pytest.mark.anyio
    async def test_strips_bot_mention(self, executor):
        prompt = executor._build_prompt('@resenhazord ver placar')

        assert '@resenhazord' not in prompt
        assert 'ver placar' in prompt

    @pytest.mark.anyio
    async def test_includes_command_list(self, executor):
        prompt = executor._build_prompt('test')

        assert 'command_list' in prompt or 'placar' in prompt.lower()

    @pytest.mark.anyio
    async def test_includes_quoted_context_block(self, executor):
        prompt = executor._build_prompt(
            'sim',
            context='Não sei te dizer..., use ,time',
        )

        assert 'Contexto da mensagem anterior' in prompt
        assert ',time' in prompt

    @pytest.mark.anyio
    async def test_omits_context_block_when_quoted_text_absent(self, executor):
        prompt = executor._build_prompt('me mande um fato')

        assert 'Contexto da mensagem anterior' not in prompt


class TestFallback:
    @pytest.mark.anyio
    async def test_returns_empty_text(self, executor):
        data = _data('@resenhazord blah')

        result = executor._fallback(data)

        assert result.text == ''

    @pytest.mark.anyio
    async def test_preserves_media_fields(self, executor):
        data = CommandData(
            text='@resenhazord blah',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
            media_is_animated=False,
            media_caption='test image',
        )

        result = executor._fallback(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'
        assert result.media_caption == 'test image'


class TestRun:
    @pytest.mark.anyio
    async def test_tool_call_resolves_to_command(self, executor, mocker):
        data = _data('@resenhazord mostrar placar dos jogos')
        _stub_chain(mocker, tool_call={'name': 'placar', 'arguments': '{"now": true}'})

        result = await executor.run(data)

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_suggest_prefix_routes_to_suggest_command(self, executor, mocker):
        data = _data('@resenhazord qual a fundação do flamengo')
        suggest_content = (
            'SUGGEST: Não sei te dizer a data exata, '
            'mas posso te mandar um time aleatório! Use ,time'
        )
        _stub_chain(mocker, content=suggest_content)

        result = await executor.run(data)

        assert result.text.startswith(',suggest:')
        assert 'Não sei' in result.text
        assert 'time' in result.text

    @pytest.mark.anyio
    async def test_clarify_prefix_routes_to_clarify_command(self, executor, mocker):
        data = _data('@resenhazord qual a tabela do brasileiro')
        _stub_chain(mocker, content='CLARIFY: Você quer ver a tabela de qual competição?')

        result = await executor.run(data)

        assert result.text.startswith(',clarify:')
        assert 'tabela' in result.text.lower()

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
            content='SUGGEST: Não posso fazer sticker dessa imagem, use ,carro!',
        )

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'


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
