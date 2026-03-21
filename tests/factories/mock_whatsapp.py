"""Mock WhatsAppPort for testing commands that need WhatsApp operations."""

from unittest.mock import AsyncMock


def create_mock_whatsapp_port(**overrides) -> AsyncMock:
    mock = AsyncMock()
    mock.group_metadata = AsyncMock(return_value={'participants': [], 'subject': 'Test Group'})
    mock.group_participants_update = AsyncMock(return_value=[])
    mock.on_whatsapp = AsyncMock(return_value=[])
    mock.send_message = AsyncMock(return_value={})
    mock.update_profile_picture = AsyncMock(return_value=None)
    mock.group_update_subject = AsyncMock(return_value=None)
    mock.group_update_description = AsyncMock(return_value=None)
    mock.send_presence_update = AsyncMock(return_value=None)
    mock.download_media = AsyncMock(return_value=b'mock-media-buffer')
    mock.create_sticker = AsyncMock(return_value=b'mock-sticker-buffer')
    for key, value in overrides.items():
        setattr(mock, key, value)
    return mock
