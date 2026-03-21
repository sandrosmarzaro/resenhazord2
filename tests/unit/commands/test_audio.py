from urllib.parse import parse_qs, urlparse

import pytest

from bot.domain.commands.audio import AudioCommand
from bot.domain.models.message import AudioContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command():
    return AudioCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', áudio hello', True),
            (',áudio hello', True),
            (', audio hello', True),
            (', ÁUDIO hello', True),
            (', áudio pt-br hello', True),
            (', áudio en-us hello', True),
            (', áudio show hello', True),
            (', áudio dm hello', True),
            ('  , áudio  hello', True),
            ('áudio', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_invalid_language_returns_error(self, command):
        data = GroupCommandDataFactory.build(text=', áudio xx-yy hello')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'idioma' in messages[0].content.text

    @pytest.mark.anyio
    async def test_no_text_returns_error(self, command):
        data = GroupCommandDataFactory.build(text=', áudio')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Cadê o texto' in messages[0].content.text

    @pytest.mark.anyio
    async def test_short_text_returns_single_audio(self, command):
        data = GroupCommandDataFactory.build(text=', áudio Hello world')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, AudioContent)
        url = messages[0].content.url
        assert 'translate.google.com/translate_tts' in url
        parsed = parse_qs(urlparse(url).query)
        assert parsed['q'] == ['Hello world']
        assert parsed['tl'] == ['pt-br']

    @pytest.mark.anyio
    async def test_custom_language(self, command):
        data = GroupCommandDataFactory.build(text=', áudio en-us Hello world')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, AudioContent)
        parsed = parse_qs(urlparse(messages[0].content.url).query)
        assert parsed['tl'] == ['en-us']

    @pytest.mark.anyio
    async def test_long_text_returns_multiple_audio_messages(self, command):
        long_text = 'Hello world. ' * 30
        data = GroupCommandDataFactory.build(text=f', áudio {long_text.strip()}')
        messages = await command.run(data)

        assert len(messages) > 1
        for msg in messages:
            assert isinstance(msg.content, AudioContent)
            assert 'translate.google.com/translate_tts' in msg.content.url

    @pytest.mark.anyio
    async def test_audio_view_once_is_true(self, command):
        data = GroupCommandDataFactory.build(text=', áudio Hello world')
        messages = await command.run(data)

        assert isinstance(messages[0].content, AudioContent)
        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', áudio Hello world', message_id='MSG_42')
        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', áudio Hello world', expiration=86400)
        messages = await command.run(data)

        assert messages[0].expiration == 86400

    @pytest.mark.anyio
    async def test_dm_flag_sends_to_participant(self, command):
        data = GroupCommandDataFactory.build(text=', áudio dm Hello world')
        messages = await command.run(data)

        assert messages[0].jid == data.participant

    @pytest.mark.anyio
    async def test_dm_flag_in_private_keeps_jid(self, command):
        data = PrivateCommandDataFactory.build(text=', áudio dm Hello world')
        messages = await command.run(data)

        assert messages[0].jid == data.jid


class TestSplitLongText:
    def test_short_text_not_split(self, command):
        result = command._split_long_text('Hello world')
        assert result == ['Hello world']

    def test_splits_on_space(self, command):
        text = 'word ' * 50
        result = command._split_long_text(text.strip())
        for chunk in result:
            assert len(chunk) <= command.MAX_CHUNK_LENGTH

    def test_splits_on_punctuation(self, command):
        text = 'Hello world. ' * 25
        result = command._split_long_text(text.strip())
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= command.MAX_CHUNK_LENGTH

    def test_exact_max_length(self, command):
        text = 'a' * 200
        result = command._split_long_text(text)
        assert result == [text]


class TestBuildTtsUrl:
    def test_url_structure(self, command):
        url = command._build_tts_url('Hello', 'en-us', 0, 1)
        parsed = urlparse(url)
        assert parsed.scheme == 'https'
        assert parsed.netloc == 'translate.google.com'
        assert parsed.path == '/translate_tts'

        params = parse_qs(parsed.query)
        assert params['q'] == ['Hello']
        assert params['tl'] == ['en-us']
        assert params['client'] == ['tw-ob']
        assert params['ie'] == ['UTF-8']
        assert params['total'] == ['1']
        assert params['idx'] == ['0']
        assert params['textlen'] == ['5']
