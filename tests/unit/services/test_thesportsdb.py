import httpx
import pytest

from bot.data.football import LEAGUES
from bot.domain.models.football import SportsDBTeam
from bot.domain.services.thesportsdb import TheSportsDBService

_BASE_URL = 'https://www.thesportsdb.com/api/v1/json/3'
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


class TestGetTeams:
    @pytest.mark.anyio
    async def test_returns_team_list(self, respx_mock, expected_team):
        respx_mock.get(url__startswith=f'{_BASE_URL}/search_all_teams.php').mock(
            return_value=httpx.Response(200, json={'teams': [_MOCK_TEAM_JSON]})
        )

        teams = await TheSportsDBService.get_teams(_LEAGUE)

        assert len(teams) == 1
        assert teams[0] == expected_team

    @pytest.mark.anyio
    async def test_returns_empty_when_null_teams(self, respx_mock):
        respx_mock.get(url__startswith=f'{_BASE_URL}/search_all_teams.php').mock(
            return_value=httpx.Response(200, json={'teams': None})
        )

        teams = await TheSportsDBService.get_teams(_LEAGUE)

        assert teams == []

    @pytest.mark.anyio
    async def test_returns_empty_on_invalid_json(self, respx_mock):
        respx_mock.get(url__startswith=f'{_BASE_URL}/search_all_teams.php').mock(
            return_value=httpx.Response(200, content=b'not json')
        )

        teams = await TheSportsDBService.get_teams(_LEAGUE)

        assert teams == []


class TestGetStandings:
    @pytest.mark.anyio
    async def test_returns_standing_rows(self, respx_mock):
        respx_mock.get(url__startswith=f'{_BASE_URL}/lookuptable.php').mock(
            return_value=httpx.Response(
                200,
                json={
                    'table': [
                        {'intRank': '1', 'strTeam': 'Manchester City'},
                        {'intRank': '2', 'strTeam': 'Arsenal'},
                    ]
                },
            )
        )

        rows = await TheSportsDBService.get_standings(_LEAGUE)

        assert len(rows) == 2
        assert rows[0].rank == 1
        assert rows[0].team == 'Manchester City'
        assert rows[1].rank == 2

    @pytest.mark.anyio
    async def test_returns_empty_when_null_table(self, respx_mock):
        respx_mock.get(url__startswith=f'{_BASE_URL}/lookuptable.php').mock(
            return_value=httpx.Response(200, json={'table': None})
        )

        rows = await TheSportsDBService.get_standings(_LEAGUE)

        assert rows == []


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


class TestFindBestMatch:
    def test_returns_none_on_empty_list(self):
        assert TheSportsDBService.find_best_match('Flamengo', []) is None

    def test_returns_best_match_by_jaccard(self):
        team_pal = SportsDBTeam(
            name='Palmeiras',
            country='Brazil',
            founded='',
            badge_url='',
            team_id='1',
            stadium='',
            capacity='',
        )
        team_flu = SportsDBTeam(
            name='Fluminense',
            country='Brazil',
            founded='',
            badge_url='',
            team_id='2',
            stadium='',
            capacity='',
        )
        result = TheSportsDBService.find_best_match('Fluminense', [team_pal, team_flu])
        assert result is team_flu

    def test_returns_none_when_no_good_match(self):
        team = SportsDBTeam(
            name='Completely Different FC',
            country='Mars',
            founded='',
            badge_url='',
            team_id='1',
            stadium='',
            capacity='',
        )
        result = TheSportsDBService.find_best_match('Fluminense', [team])
        assert result is None

    def test_score_candidate_returns_jaccard_and_ratio(self):
        tm_tokens = {'fluminense'}
        t_tokens = {'fluminense'}
        jaccard, ratio = TheSportsDBService._score_candidate(
            'Fluminense', tm_tokens, 'Fluminense', t_tokens
        )
        assert jaccard == 1.0
        assert ratio == 1.0
