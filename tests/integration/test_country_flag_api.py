import pytest

from bot.infrastructure.restcountries_client import RestCountriesClient
from bot.settings import Settings

pytestmark = pytest.mark.external


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def api_key():
    key = Settings().restcountries_api_key
    if not key:
        pytest.skip('RESTCOUNTRIES_API_KEY not set')
    return key


@pytest.fixture(autouse=True)
def reset_cache():
    RestCountriesClient.reset_cache()
    yield
    RestCountriesClient.reset_cache()


class TestRestCountriesV5Contract:
    @pytest.mark.anyio
    async def test_fetch_returns_objects_with_fields_the_command_reads(self, api_key):
        countries = await RestCountriesClient(api_key).fetch()

        assert len(countries) > 100
        country = countries[0]
        assert country['names']['common']
        assert country['flag']['url_png'].startswith('http')
        assert country['codes']['alpha_3']
        assert isinstance(country['capitals'], list)
        assert country['area']['kilometers'] > 0
