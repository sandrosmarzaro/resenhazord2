import httpx
import pytest

from bot.data.football import LEAGUES
from bot.domain.models.football import SportsDBTeam
from bot.domain.services.thesportsdb import TheSportsDBService

_BASE_URL = 'https://www.thesportsdb.com/api/v1/json/123'
_LEAGUE = LEAGUES['pl']

_MOCK_TEAM_JSON = {
    'strTeam': 'Manchester City',
    'strCountry': 'England',
    'intFormedYear': '1880',
    'strBadge': 'https://www.thesportsdb.com/images/media/team/badge/man-city.png',
    'idTeam': '133613',
    'strStadium': 'City of Manchester Stadium',
    'intStadiumCapacity': '55097',
}


@pytest.fixture
def expected_team() -> SportsDBTeam:
    return SportsDBTeam(
        name='Manchester City',
        country='England',
        founded='1880',
        badge_url='https://www.thesportsdb.com/images/media/team/badge/man-city.png',
        team_id='133613',
        stadium='City of Manchester Stadium',
        capacity='55097',
    )


class TestSearchTeam:
    @pytest.mark.anyio
    async def test_returns_first_match(self, respx_mock, expected_team):
        respx_mock.get(url__startswith=f'{_BASE_URL}/searchteams.php').mock(
            return_value=httpx.Response(200, json={'teams': [_MOCK_TEAM_JSON]})
        )

        team = await TheSportsDBService.search_team('Manchester City')

        assert team == expected_team

    @pytest.mark.anyio
    async def test_returns_none_when_no_results(self, respx_mock):
        respx_mock.get(url__startswith=f'{_BASE_URL}/searchteams.php').mock(
            return_value=httpx.Response(200, json={'teams': None})
        )

        team = await TheSportsDBService.search_team('Unknown')

        assert team is None

    @pytest.mark.anyio
    async def test_returns_none_on_empty_list(self, respx_mock):
        respx_mock.get(url__startswith=f'{_BASE_URL}/searchteams.php').mock(
            return_value=httpx.Response(200, json={'teams': []})
        )

        team = await TheSportsDBService.search_team('Nonexistent')

        assert team is None
