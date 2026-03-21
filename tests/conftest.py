import pytest

from bot.application.command_registry import CommandRegistry
from bot.infrastructure.http_client import HttpClient
from bot.infrastructure.mongodb import MongoDBConnection


@pytest.fixture(autouse=True)
def _reset_singletons():
    CommandRegistry.reset()
    HttpClient.reset()
    MongoDBConnection.reset()
    yield
    CommandRegistry.reset()
    HttpClient.reset()
    MongoDBConnection.reset()


@pytest.fixture
def mock_whatsapp(mocker):
    mock = mocker.AsyncMock()
    mock.group_metadata = mocker.AsyncMock(
        return_value={'participants': [], 'subject': 'Test Group'}
    )
    mock.group_participants_update = mocker.AsyncMock(return_value=[])
    mock.on_whatsapp = mocker.AsyncMock(return_value=[])
    mock.send_message = mocker.AsyncMock(return_value={})
    mock.update_profile_picture = mocker.AsyncMock(return_value=None)
    mock.group_update_subject = mocker.AsyncMock(return_value=None)
    mock.group_update_description = mocker.AsyncMock(return_value=None)
    mock.send_presence_update = mocker.AsyncMock(return_value=None)
    mock.download_media = mocker.AsyncMock(return_value=b'mock-media-buffer')
    mock.create_sticker = mocker.AsyncMock(return_value=b'mock-sticker-buffer')
    return mock


@pytest.fixture
def mock_mongodb_collection(mocker):
    def _factory(collection_name: str):
        collection = mocker.AsyncMock()
        mocker.patch(
            'bot.infrastructure.mongodb.MongoDBConnection.collection',
            return_value=collection,
        )
        return collection

    return _factory


@pytest.fixture
def mock_subprocess(mocker):
    def _factory(target: str, *, calls: list[tuple[bytes, bytes, int]]):
        procs = []
        for stdout, stderr, returncode in calls:
            proc = mocker.AsyncMock()
            proc.communicate.return_value = (stdout, stderr)
            proc.returncode = returncode
            procs.append(proc)

        return mocker.patch(target, side_effect=procs)

    return _factory
