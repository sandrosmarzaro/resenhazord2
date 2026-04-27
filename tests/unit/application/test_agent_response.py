import pytest

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.domain.models.command_data import CommandData


@pytest.fixture
def translator() -> AgentResponseTranslator:
    return AgentResponseTranslator(CommandRegistry.instance())


class TestTranslateBasics:
    @pytest.mark.anyio
    async def test_simple_flag_argument(self, translator):
        data = _data('@resenhazord ver placar')

        result = translator.translate(data, 'placar', '{"now": true}')

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_text_args_appended_after_flags(self, translator):
        data = _data('@resenhazord áudio')

        result = translator.translate(data, 'áudio', '{"args": "hello world"}')

        assert result.text == ',áudio hello world'

    @pytest.mark.anyio
    async def test_flags_and_args_combined(self, translator):
        data = _data('@resenhazord áudio')

        result = translator.translate(data, 'áudio', '{"dm": true, "args": "test text"}')

        assert 'dm' in result.text
        assert 'test text' in result.text

    @pytest.mark.anyio
    async def test_false_flags_omitted(self, translator):
        data = _data('@resenhazord teste')

        result = translator.translate(data, 'test', '{"verbose": false, "debug": true}')

        assert result.text == ',test debug'

    @pytest.mark.anyio
    async def test_empty_arguments(self, translator):
        data = _data('@resenhazord ola')

        result = translator.translate(data, 'oi', '')

        assert result.text == ',oi'

    @pytest.mark.anyio
    async def test_command_key_filtered_from_arguments(self, translator):
        data = _data(
            '@resenhazord ver tabela do brasil',
            jid='test@g.us',
            is_group=True,
        )

        result = translator.translate(data, 'tabela', '{"command": "tabela", "liga": "br"}')

        assert 'command' not in result.text
        assert ',tabela' in result.text
        assert 'br' in result.text


class TestTranslateDmRedirect:
    @pytest.mark.anyio
    async def test_dm_keyword_redirects_to_sender_in_group(self, translator):
        data = _data(
            '@resenhazord ver placar privado',
            jid='test@g.us',
            sender_jid='user@s.whatsapp.net',
            is_group=True,
        )

        result = translator.translate(data, 'placar', '{"now": true}')

        assert result.jid == 'user@s.whatsapp.net'
        assert result.is_group is True

    @pytest.mark.anyio
    async def test_dm_keyword_ignored_outside_group(self, translator):
        data = _data(
            '@resenhazord ver placar privado',
            jid='user@s.whatsapp.net',
            sender_jid='user@s.whatsapp.net',
            is_group=False,
        )

        result = translator.translate(data, 'placar', '{"now": true}')

        assert result.jid == 'user@s.whatsapp.net'


class TestTranslateNormalisation:
    @pytest.mark.anyio
    async def test_strips_double_dash_prefix_from_flags(self, translator):
        data = _data(
            '@resenhazord ver tabela br g4',
            jid='test@g.us',
            sender_jid='user@s.whatsapp.net',
            is_group=True,
        )

        result = translator.translate(data, 'tabela', '{"g4": true}')

        assert 'g4' in result.text
        assert '--' not in result.text

    @pytest.mark.anyio
    async def test_preserves_media_fields(self, translator):
        data = CommandData(
            text='make sticker',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
            media_is_animated=False,
        )

        result = translator.translate(data, 'stic', '')

        assert result.text == ',stic'
        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'


def _data(
    text: str,
    *,
    jid: str = 'test@g.us',
    sender_jid: str = 'test@s.whatsapp.net',
    is_group: bool = False,
) -> CommandData:
    return CommandData(text=text, jid=jid, sender_jid=sender_jid, is_group=is_group)
