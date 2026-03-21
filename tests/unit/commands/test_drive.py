from unittest.mock import AsyncMock

import pytest

from bot.domain.commands.drive import DriveCommand
from bot.domain.services.discord import DiscordService
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory
from tests.factories.mock_whatsapp import create_mock_whatsapp_port


def _create_mock_discord() -> AsyncMock:
    mock = AsyncMock(spec=DiscordService)
    mock.CATEGORY_TYPE = DiscordService.CATEGORY_TYPE
    mock.TEXT_CHANNEL_TYPE = DiscordService.TEXT_CHANNEL_TYPE
    mock.get_channels = AsyncMock(return_value=[])
    mock.find_category = DiscordService.find_category.__get__(mock)
    mock.find_channel = DiscordService.find_channel.__get__(mock)
    mock.create_category = AsyncMock(return_value={'id': 'cat-1', 'name': '2026', 'type': 4})
    mock.create_channel = AsyncMock(
        return_value={'id': 'ch-1', 'name': 'churrasco', 'type': 0, 'parent_id': 'cat-1'}
    )
    mock.upload_media = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_whatsapp():
    return create_mock_whatsapp_port()


@pytest.fixture
def mock_discord():
    return _create_mock_discord()


@pytest.fixture
def command(mock_whatsapp, mock_discord):
    cmd = DriveCommand(discord=mock_discord)
    cmd._whatsapp = mock_whatsapp
    return cmd


MESSAGE_ID = 'MSG_55'
EXISTING_CATEGORY = {'id': 'cat-1', 'name': '2026', 'type': 4}
EXISTING_CHANNEL = {
    'id': 'ch-1',
    'name': 'churrasco',
    'type': 0,
    'parent_id': 'cat-1',
}


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',drive 2026 churrasco', True),
            (', drive 2026 churrasco', True),
            (',DRIVE 2026 churrasco', True),
            (',drive', False),
            ('drive 2026 churrasco', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestGroupOnly:
    @pytest.mark.anyio
    async def test_rejects_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=',drive 2026 churrasco')

        messages = await command.run(data)

        assert 'grupo' in messages[0].content.text.lower()


class TestNoMedia:
    @pytest.mark.anyio
    async def test_no_media(self, command):
        data = GroupCommandDataFactory.build(text=',drive 2026 churrasco')

        messages = await command.run(data)

        assert 'mídia' in messages[0].content.text.lower()


class TestMissingArgs:
    @pytest.mark.anyio
    async def test_missing_channel(self, command):
        data = GroupCommandDataFactory.build(
            text=',drive 2026',
            media_type='image',
            media_source='direct',
        )

        messages = await command.run(data)

        assert 'Uso:' in messages[0].content.text


class TestCategoryNotFound:
    @pytest.mark.anyio
    async def test_without_new_flag(self, command, mock_discord):
        mock_discord.get_channels.return_value = []
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert '2026' in messages[0].content.text
        assert 'não encontrada' in messages[0].content.text


class TestChannelNotFound:
    @pytest.mark.anyio
    async def test_without_new_flag(self, command, mock_discord):
        mock_discord.get_channels.return_value = [EXISTING_CATEGORY]
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert 'churrasco' in messages[0].content.text
        assert 'não encontrado' in messages[0].content.text


class TestNewFlag:
    @pytest.mark.anyio
    async def test_creates_both(self, command, mock_discord, mock_whatsapp):
        mock_discord.get_channels.return_value = []
        mock_whatsapp.download_media = AsyncMock(return_value=b'img-data')
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco new',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        mock_discord.create_category.assert_called_once_with('2026')
        mock_discord.create_channel.assert_called_once_with('churrasco', 'cat-1')
        mock_discord.upload_media.assert_called_once()
        assert '2026' in messages[0].content.text
        assert 'churrasco' in messages[0].content.text
        assert '✅' in messages[0].content.text

    @pytest.mark.anyio
    async def test_creates_only_channel(self, command, mock_discord, mock_whatsapp):
        mock_discord.get_channels.return_value = [EXISTING_CATEGORY]
        mock_whatsapp.download_media = AsyncMock(return_value=b'img-data')
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco new',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        mock_discord.create_category.assert_not_called()
        mock_discord.create_channel.assert_called_once_with('churrasco', 'cat-1')


class TestSuccessfulUpload:
    @pytest.mark.anyio
    async def test_image_upload(self, command, mock_discord, mock_whatsapp):
        mock_discord.get_channels.return_value = [EXISTING_CATEGORY, EXISTING_CHANNEL]
        mock_whatsapp.download_media = AsyncMock(return_value=b'img-data')
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        mock_discord.upload_media.assert_called_once()
        call_args = mock_discord.upload_media.call_args
        assert call_args[0][0] == 'ch-1'
        assert call_args[0][1] == b'img-data'
        assert call_args[0][2].startswith('image_')
        assert call_args[0][2].endswith('.jpg')
        assert '✅' in messages[0].content.text

    @pytest.mark.anyio
    async def test_video_upload(self, command, mock_discord, mock_whatsapp):
        mock_discord.get_channels.return_value = [EXISTING_CATEGORY, EXISTING_CHANNEL]
        mock_whatsapp.download_media = AsyncMock(return_value=b'vid-data')
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco',
            media_type='video',
            media_source='quoted',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        call_args = mock_discord.upload_media.call_args
        assert call_args[0][2].startswith('video_')
        assert call_args[0][2].endswith('.mp4')

    @pytest.mark.anyio
    async def test_audio_upload(self, command, mock_discord, mock_whatsapp):
        mock_discord.get_channels.return_value = [EXISTING_CATEGORY, EXISTING_CHANNEL]
        mock_whatsapp.download_media = AsyncMock(return_value=b'aud-data')
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco',
            media_type='audio',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        call_args = mock_discord.upload_media.call_args
        assert call_args[0][2].startswith('audio_')
        assert call_args[0][2].endswith('.ogg')

    @pytest.mark.anyio
    async def test_calls_download_media(self, command, mock_discord, mock_whatsapp):
        mock_discord.get_channels.return_value = [EXISTING_CATEGORY, EXISTING_CHANNEL]
        mock_whatsapp.download_media = AsyncMock(return_value=b'data')
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco',
            media_type='image',
            media_source='quoted',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        mock_whatsapp.download_media.assert_called_once_with(MESSAGE_ID, 'quoted')


class TestUploadError:
    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command, mock_discord, mock_whatsapp):
        mock_discord.get_channels.return_value = [EXISTING_CATEGORY, EXISTING_CHANNEL]
        mock_whatsapp.download_media = AsyncMock(return_value=b'data')
        mock_discord.upload_media.side_effect = RuntimeError('upload failed')
        data = GroupCommandDataFactory.build(
            text=',drive 2026 churrasco',
            media_type='image',
            media_source='direct',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert 'Erro' in messages[0].content.text
        assert 'Drive' in messages[0].content.text
