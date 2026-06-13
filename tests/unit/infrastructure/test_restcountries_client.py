import httpx
import pytest

from bot.infrastructure.restcountries_client import RestCountriesClient

V5_URL = 'https://api.restcountries.com/countries/v5'


@pytest.fixture
def client():
    return RestCountriesClient(api_key='rc_live_test')


@pytest.fixture(autouse=True)
def reset_cache():
    RestCountriesClient.reset_cache()
    yield
    RestCountriesClient.reset_cache()


def _page(count):
    objects = [{'names': {'common': f'Country{index}'}} for index in range(count)]
    return httpx.Response(200, json={'data': {'objects': objects, 'meta': {'total': count}}})


class TestFetch:
    @pytest.mark.anyio
    async def test_sends_bearer_token(self, client, respx_mock):
        route = respx_mock.get(url__startswith=V5_URL).mock(return_value=_page(1))

        await client.fetch()

        assert route.calls.last.request.headers['Authorization'] == 'Bearer rc_live_test'

    @pytest.mark.anyio
    async def test_follows_pagination_until_short_page(self, client, respx_mock):
        route = respx_mock.get(url__startswith=V5_URL).mock(
            side_effect=[_page(RestCountriesClient.PAGE_SIZE), _page(3)]
        )

        countries = await client.fetch()

        assert route.call_count == 2
        assert len(countries) == RestCountriesClient.PAGE_SIZE + 3

    @pytest.mark.anyio
    async def test_caches_across_calls(self, client, respx_mock):
        route = respx_mock.get(url__startswith=V5_URL).mock(return_value=_page(2))

        await client.fetch()
        await client.fetch()

        assert route.call_count == 1

    @pytest.mark.anyio
    async def test_reset_cache_forces_refetch(self, client, respx_mock):
        route = respx_mock.get(url__startswith=V5_URL).mock(return_value=_page(2))

        await client.fetch()
        RestCountriesClient.reset_cache()
        await client.fetch()

        assert route.call_count == 2

    @pytest.mark.anyio
    async def test_raises_on_http_error(self, client, respx_mock):
        respx_mock.get(url__startswith=V5_URL).mock(return_value=httpx.Response(401))

        with pytest.raises(httpx.HTTPStatusError):
            await client.fetch()
