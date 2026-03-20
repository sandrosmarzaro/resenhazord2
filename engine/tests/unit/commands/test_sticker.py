from unittest.mock import AsyncMock

import pytest

from bot.domain.commands.sticker import StickerCommand
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_whatsapp import create_mock_whatsapp_port


@pytest.fixture
def mock_whatsapp():
    return create_mock_whatsapp_port()


@pytest.fixture
def command(mock_whatsapp):
    cmd = StickerCommand()
    cmd._whatsapp = mock_whatsapp
    return cmd


MESSAGE_ID = 'MSG_42'


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
            (', sticker', False),
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
    async def test_creates_sticker_from_direct_image(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'image-data')
        mock_whatsapp.create_sticker = AsyncMock(return_value=b'sticker-data')
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.data == b'sticker-data'
        mock_whatsapp.download_media.assert_called_once_with(MESSAGE_ID, 'direct')
        mock_whatsapp.create_sticker.assert_called_once_with(b'image-data', 'full')

    @pytest.mark.anyio
    async def test_creates_sticker_from_quoted_video(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'video-data')
        mock_whatsapp.create_sticker = AsyncMock(return_value=b'sticker-data')
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='video',
            media_source='quoted',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        mock_whatsapp.download_media.assert_called_once_with(MESSAGE_ID, 'quoted')
        mock_whatsapp.create_sticker.assert_called_once_with(b'video-data', 'full')

    @pytest.mark.anyio
    async def test_sticker_type_option(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'image-data')
        mock_whatsapp.create_sticker = AsyncMock(return_value=b'sticker-data')
        data = GroupCommandDataFactory.build(
            text=',stic crop',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        mock_whatsapp.create_sticker.assert_called_once_with(b'image-data', 'crop')

    @pytest.mark.anyio
    @pytest.mark.parametrize('sticker_type', ['crop', 'full', 'circle', 'rounded'])
    async def test_all_sticker_types(self, command, mock_whatsapp, sticker_type):
        mock_whatsapp.download_media = AsyncMock(return_value=b'data')
        mock_whatsapp.create_sticker = AsyncMock(return_value=b'sticker')
        data = GroupCommandDataFactory.build(
            text=f',stic {sticker_type}',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        mock_whatsapp.create_sticker.assert_called_once_with(b'data', sticker_type)

    @pytest.mark.anyio
    async def test_returns_sticker_content(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'img')
        mock_whatsapp.create_sticker = AsyncMock(return_value=b'webp-sticker')
        data = GroupCommandDataFactory.build(
            text=',stic',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert messages[0].content.type == 'sticker'
        assert messages[0].content.data == b'webp-sticker'
