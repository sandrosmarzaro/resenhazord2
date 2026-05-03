import httpx
import pytest
import respx

from bot.infrastructure.http_client import HttpClient


@pytest.fixture(autouse=True)
def reset_client():
    HttpClient.reset()
    yield
    HttpClient.reset()


class TestGet:
    @pytest.mark.anyio
    async def test_passes_url_and_returns_response(self):
        with respx.mock() as mock:
            mock.get('https://api.example.com/ping').respond(200, text='pong')

            response = await HttpClient.get('https://api.example.com/ping')

        assert response.status_code == httpx.codes.OK
        assert response.text == 'pong'

    @pytest.mark.anyio
    async def test_tolerates_headers_none(self):
        with respx.mock() as mock:
            mock.get('https://api.example.com/ping').respond(200)

            await HttpClient.get('https://api.example.com/ping', headers=None)

    @pytest.mark.anyio
    async def test_merges_caller_headers(self):
        with respx.mock() as mock:
            route = mock.get('https://api.example.com/ping').respond(200)

            await HttpClient.get('https://api.example.com/ping', headers={'X-Test': 'yes'})

        assert route.calls.last.request.headers['X-Test'] == 'yes'


class TestPost:
    @pytest.mark.anyio
    async def test_tolerates_headers_none(self):
        with respx.mock() as mock:
            mock.post('https://api.example.com/ping').respond(200)

            await HttpClient.post('https://api.example.com/ping', headers=None)
