from unittest.mock import AsyncMock

import pytest

from bot.domain.commands.scarra import ScarraCommand
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory
from tests.factories.mock_whatsapp import create_mock_whatsapp_port


@pytest.fixture
def mock_whatsapp():
    return create_mock_whatsapp_port()


@pytest.fixture
def command(mock_whatsapp):
    cmd = ScarraCommand()
    cmd._whatsapp = mock_whatsapp
    return cmd


MESSAGE_ID = 'MSG_77'


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',scarra', True),
            (', scarra', True),
            (', SCARRA', True),
            ('scarra', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestGroupOnly:
    @pytest.mark.anyio
    async def test_rejects_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=',scarra')

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'grupo' in messages[0].content.text.lower()


class TestNoViewOnce:
    @pytest.mark.anyio
    async def test_no_media(self, command):
        data = GroupCommandDataFactory.build(text=',scarra')

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'mensagem única' in messages[0].content.text

    @pytest.mark.anyio
    async def test_non_view_once_media(self, command):
        data = GroupCommandDataFactory.build(
            text=',scarra',
            media_type='image',
            media_source='quoted',
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'mensagem única' in messages[0].content.text


class TestImageViewOnce:
    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'img-data')
        data = GroupCommandDataFactory.build(
            text=',scarra',
            media_type='image',
            media_source='view_once',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.type == 'image_buffer'
        assert messages[0].content.data == b'img-data'
        assert messages[0].content.caption == 'Escarrado! 😝'
        mock_whatsapp.download_media.assert_called_once_with(MESSAGE_ID, 'view_once')

    @pytest.mark.anyio
    async def test_uses_original_caption(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'img-data')
        data = GroupCommandDataFactory.build(
            text=',scarra',
            media_type='image',
            media_source='view_once',
            media_caption='foto secreta',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert messages[0].content.caption == 'foto secreta'


class TestVideoViewOnce:
    @pytest.mark.anyio
    async def test_returns_video_buffer(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'vid-data')
        data = GroupCommandDataFactory.build(
            text=',scarra',
            media_type='video',
            media_source='view_once',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.type == 'video_buffer'
        assert messages[0].content.data == b'vid-data'
        assert messages[0].content.caption == 'Escarrado! 😝'


class TestAudioViewOnce:
    @pytest.mark.anyio
    async def test_returns_audio_buffer(self, command, mock_whatsapp):
        mock_whatsapp.download_media = AsyncMock(return_value=b'aud-data')
        data = GroupCommandDataFactory.build(
            text=',scarra',
            media_type='audio',
            media_source='view_once',
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.type == 'audio_buffer'
        assert messages[0].content.data == b'aud-data'
