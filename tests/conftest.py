from typing import Any

import httpx
import pytest
from faker import Faker
from pydantic import BaseModel

from bot.application.command_registry import CommandRegistry
from bot.infrastructure.http_client import HttpClient
from bot.infrastructure.mongodb import MongoDBConnection


class TestSettings(BaseModel):
    tmdb_api_key: str = 'test-tmdb-key'
    omdb_api_key: str = 'test-omdb-key'
    jamendo_client_id: str = 'test-client-id'
    bot_jid: str = '5500000000000@s.whatsapp.net'


@pytest.fixture
def faker() -> Faker:
    return Faker(['pt_BR', 'en_US'])


@pytest.fixture
def test_settings() -> TestSettings:
    return TestSettings()


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
def mock_dev_list(mocker):
    dev_list = mocker.AsyncMock()
    dev_list.is_dev.return_value = False
    return dev_list


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


@pytest.fixture
def wiki_route(respx_mock):
    return respx_mock.get(url__startswith='https://en.wikipedia.org/api/rest_v1/page/summary/')


@pytest.fixture
def wiki_image_route(respx_mock):
    return respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
        return_value=httpx.Response(200, content=b'fake-image')
    )


@pytest.fixture
def translate_route(respx_mock):
    return respx_mock.get(
        url__startswith='https://translate.googleapis.com/translate_a/single'
    ).mock(return_value=httpx.Response(200, json=[[['Translated text.', 'original']]]))


@pytest.fixture
def generic_image_route(respx_mock):
    return respx_mock.get(url__startswith='https://').mock(
        return_value=httpx.Response(200, content=b'fake-image-data')
    )


def make_group_participants(
    *jids: str,
    bot_jid: str = '5500000000000@s.whatsapp.net',
    bot_admin: bool = True,
    owner: str | None = None,
    owner_admin: bool = False,
) -> dict[str, Any]:
    participants = []
    for jid in jids:
        entry: dict[str, Any] = {'id': jid, 'admin': None}
        if jid == bot_jid and bot_admin:
            entry['admin'] = 'admin'
        if jid == owner and owner_admin:
            entry['admin'] = 'admin'
        participants.append(entry)
    return {'participants': participants, 'owner': owner}


@pytest.fixture
def pokemon_api_route(respx_mock):
    return respx_mock.get(url__startswith='https://pokeapi.co/api/v2/pokemon/')


@pytest.fixture
def pokemon_image_route(respx_mock):
    return respx_mock.get(url__startswith='https://raw.githubusercontent.com/').mock(
        return_value=httpx.Response(200, content=b'fake-pokemon-image')
    )


@pytest.fixture
def tmdb_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.themoviedb.org/')


@pytest.fixture
def omdb_route(respx_mock):
    return respx_mock.get(url__startswith='http://www.omdbapi.com/')


@pytest.fixture
def deezer_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.deezer.com/chart/')


@pytest.fixture
def jamendo_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.jamendo.com/')


@pytest.fixture
def hitomi_gallery_route(respx_mock):
    return respx_mock.get(url__startswith='https://ltn.gold-usergeneratedcontent.net/galleries/')


@pytest.fixture
def hitomi_cover_route(respx_mock):
    return respx_mock.get(url__startswith='https://tn.gold-usergeneratedcontent.net/').mock(
        return_value=httpx.Response(200, content=b'fake-cover')
    )


@pytest.fixture
def nhentai_api_route(respx_mock):
    return respx_mock.get(url__startswith='https://nhentai.to/api/galleries/search')


@pytest.fixture
def nhentai_cover_route(respx_mock):
    return respx_mock.get(url__startswith='https://t.nhentai.net/galleries/').mock(
        return_value=httpx.Response(200, content=b'fake-nhentai-cover')
    )


@pytest.fixture
def ban_command_instance(mock_whatsapp):
    from bot.domain.commands.ban import BanCommand

    return BanCommand(bot_jid='5500000000000@s.whatsapp.net', whatsapp=mock_whatsapp)
