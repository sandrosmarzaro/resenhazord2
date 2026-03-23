import pytest

from bot.domain.commands.sticker import StickerCommand
from tests.factories.command_data import GroupCommandDataFactory

MESSAGE_ID = 'MSG_42'


@pytest.fixture
def command(mock_whatsapp):
    cmd = StickerCommand()
    cmd._whatsapp = mock_whatsapp
    return cmd


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',stic', True),
            (', stic', True),
            (', STIC', True),
            (', stic crop', True),
            (', stic full', True),
            (', stic circle', True),
            (', stic rounded', True),
            (', sticker', True),
            (', fig', True),
            (', figurinha', True),
            (', stic Anime | Sandro', True),
            (', stic crop Anime | Sandro', True),
            (', sticker Meu Pack', True),
            ('stic', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestNoMedia:
    @pytest.mark.anyio
    async def test_no_media_returns_error(self, command):
        data = GroupCommandDataFactory.build(text=',stic')

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'imagem' in messages[0].content.text
        assert 'gif' in messages[0].content.text

    @pytest.mark.anyio
    async def test_wrong_media_type_returns_error(self, command):
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='sticker',
            media_source='quoted',
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'imagem' in messages[0].content.text

    @pytest.mark.anyio
    async def test_audio_media_returns_error(self, command):
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='audio',
            media_source='direct',
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'imagem' in messages[0].content.text


class TestStickerCreation:
    @pytest.mark.anyio
    async def test_creates_sticker_from_direct_image(self, command, mock_whatsapp, mocker):
        mock_whatsapp.download_media.return_value = b'image-data'
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker-data',
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.data == b'sticker-data'
        mock_whatsapp.download_media.assert_called_once_with(MESSAGE_ID, 'direct')
        mock_create.assert_called_once_with(b'image-data', 'full', '', '')

    @pytest.mark.anyio
    async def test_creates_sticker_from_quoted_video(self, command, mock_whatsapp, mocker):
        mock_whatsapp.download_media.return_value = b'video-data'
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='video',
            media_source='quoted',
            message_id=MESSAGE_ID,
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker-data',
        )

        await command.run(data)

        mock_whatsapp.download_media.assert_called_once_with(MESSAGE_ID, 'quoted')
        mock_create.assert_called_once_with(b'video-data', 'full', '', '')

    @pytest.mark.anyio
    async def test_sticker_type_option(self, command, mock_whatsapp, mocker):
        mock_whatsapp.download_media.return_value = b'image-data'
        data = GroupCommandDataFactory.build(
            text=',stic crop',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker-data',
        )

        await command.run(data)

        mock_create.assert_called_once_with(b'image-data', 'crop', '', '')

    @pytest.mark.anyio
    @pytest.mark.parametrize('sticker_type', ['crop', 'full', 'circle', 'rounded'])
    async def test_all_sticker_types(self, command, mock_whatsapp, mocker, sticker_type):
        mock_whatsapp.download_media.return_value = b'data'
        data = GroupCommandDataFactory.build(
            text=f',stic {sticker_type}',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker',
        )

        await command.run(data)

        mock_create.assert_called_once_with(b'data', sticker_type, '', '')

    @pytest.mark.anyio
    async def test_returns_sticker_content(self, command, mock_whatsapp, mocker):
        mock_whatsapp.download_media.return_value = b'img'
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )
        mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'webp-sticker',
        )

        messages = await command.run(data)

        assert messages[0].content.type == 'sticker'
        assert messages[0].content.data == b'webp-sticker'

    @pytest.mark.anyio
    async def test_uses_proactive_media_buffer(self, command, mock_whatsapp, mocker):
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
            media_buffer=b'proactive-image',
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker-data',
        )

        messages = await command.run(data)

        assert len(messages) == 1
        mock_whatsapp.download_media.assert_not_called()
        mock_create.assert_called_once_with(b'proactive-image', 'full', '', '')


class TestPackAuthor:
    @pytest.mark.anyio
    async def test_custom_pack_and_author(self, command, mock_whatsapp, mocker):
        mock_whatsapp.download_media.return_value = b'img'
        data = GroupCommandDataFactory.build(
            text=',stic Anime | Sandro',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker',
        )

        await command.run(data)

        mock_create.assert_called_once_with(b'img', 'full', 'Anime', 'Sandro')

    @pytest.mark.anyio
    async def test_custom_pack_only(self, command, mock_whatsapp, mocker):
        mock_whatsapp.download_media.return_value = b'img'
        data = GroupCommandDataFactory.build(
            text=',stic Meu Pack',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker',
        )

        await command.run(data)

        mock_create.assert_called_once_with(b'img', 'full', 'Meu Pack', '')

    @pytest.mark.anyio
    async def test_custom_pack_with_type(self, command, mock_whatsapp, mocker):
        mock_whatsapp.download_media.return_value = b'img'
        data = GroupCommandDataFactory.build(
            text=',stic crop Anime | Sandro',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )
        mock_create = mocker.patch(
            'bot.domain.commands.sticker.StickerCreator.create',
            return_value=b'sticker',
        )

        await command.run(data)

        mock_create.assert_called_once_with(b'img', 'crop', 'Anime', 'Sandro')


class TestParsePackAuthor:
    def test_empty_args(self, command):
        assert command._parse_pack_author('') == ('', '')

    def test_pack_only(self, command):
        assert command._parse_pack_author('Anime') == ('Anime', '')

    def test_pack_and_author(self, command):
        assert command._parse_pack_author('Anime | Sandro') == ('Anime', 'Sandro')

    def test_pipe_with_spaces(self, command):
        assert command._parse_pack_author('My Pack | My Author') == ('My Pack', 'My Author')

    def test_pipe_without_spaces(self, command):
        assert command._parse_pack_author('Pack|Author') == ('Pack', 'Author')
