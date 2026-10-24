import httpx
import pytest

from bot.data.espn_leagues import ScoreboardLeague
from bot.data.football import LEAGUES
from bot.domain.models.football import MatchStatus, TmLiveMatch, TmStandingRow
from bot.domain.services.espn import EspnService

_STANDINGS_URL = 'https://site.api.espn.com/apis/v2/sports/soccer/bra.1/standings'
_SCOREBOARD_URL = 'https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/scoreboard'


def _entry(team: str, rank: int, points: int, goal_diff: int = 0) -> dict:
    stats = {
        'rank': rank,
        'gamesPlayed': 31,
        'wins': 20,
        'ties': 7,
        'losses': 4,
        'pointsFor': 61,
        'pointsAgainst': 25,
        'pointDifferential': goal_diff,
        'points': points,
    }
    return {
        'team': {'displayName': team},
        'stats': [{'name': name, 'value': float(value)} for name, value in stats.items()],
    }


def _standings(*groups: list[dict]) -> httpx.Response:
    children = [{'standings': {'entries': entries}} for entries in groups]
    return httpx.Response(200, json={'children': children})


class TestFetchStandings:
    @pytest.mark.anyio
    async def test_maps_entries_to_rows_in_rank_order(self, respx_mock):
        respx_mock.get(_STANDINGS_URL).mock(
            return_value=_standings(
                [_entry('Palmeiras', 2, 60, goal_diff=20), _entry('Flamengo', 1, 67, 36)]
            )
        )

        rows = await EspnService.fetch_standings(LEAGUES['br'])

        assert rows == [
            TmStandingRow(
                rank=1,
                team='Flamengo',
                matches=31,
                wins=20,
                draws=7,
                losses=4,
                goals_for=61,
                goals_against=25,
                goal_diff=36,
                points=67,
            ),
            TmStandingRow(
                rank=2,
                team='Palmeiras',
                matches=31,
                wins=20,
                draws=7,
                losses=4,
                goals_for=61,
                goals_against=25,
                goal_diff=20,
                points=60,
            ),
        ]

    @pytest.mark.anyio
    async def test_merges_groups_into_one_table_by_points(self, respx_mock):
        respx_mock.get(_STANDINGS_URL).mock(
            return_value=_standings(
                [_entry('Boca', 1, 30, goal_diff=5), _entry('Lanus', 2, 20)],
                [_entry('River', 1, 30, goal_diff=9)],
            )
        )

        rows = await EspnService.fetch_standings(LEAGUES['br'])

        assert [(row.rank, row.team) for row in rows] == [(1, 'River'), (2, 'Boca'), (3, 'Lanus')]

    @pytest.mark.anyio
    async def test_league_without_standings_returns_empty(self, respx_mock):
        respx_mock.get(_STANDINGS_URL).mock(return_value=httpx.Response(200, json={}))

        rows = await EspnService.fetch_standings(LEAGUES['br'])

        assert rows == []


def _event(state: str, **overrides) -> dict:
    status_names = {
        'pre': 'STATUS_SCHEDULED',
        'in': 'STATUS_SECOND_HALF',
        'post': 'STATUS_FULL_TIME',
    }
    event = {
        'id': '401',
        'date': '2026-10-24T19:30Z',
        'competitions': [
            {
                'status': {
                    'displayClock': "67'",
                    'type': {'name': status_names[state], 'state': state},
                },
                'competitors': [
                    {'homeAway': 'away', 'team': {'shortDisplayName': 'Palmeiras'}, 'score': '1'},
                    {'homeAway': 'home', 'team': {'shortDisplayName': 'Flamengo'}, 'score': '2'},
                ],
            }
        ],
    }
    status = event['competitions'][0]['status']
    status['type']['name'] = overrides.pop('status_name', status['type']['name'])
    return {**event, **overrides}


def _scoreboard(*events: dict) -> httpx.Response:
    return httpx.Response(200, json={'events': list(events)})


class TestFetchScoreboard:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.fixture
    def leagues(self, mocker):
        league = ScoreboardLeague(slug='bra.1', name='Brasileirão', flag='🇧🇷')
        mocker.patch('bot.domain.services.espn.SCOREBOARD_LEAGUES', (league,))

    @pytest.fixture
    def scoreboard_route(self, respx_mock, leagues):
        return respx_mock.get(_SCOREBOARD_URL)

    @pytest.mark.anyio
    async def test_maps_live_event(self, scoreboard_route):
        scoreboard_route.mock(return_value=_scoreboard(_event('in')))

        matches = await EspnService.fetch_scoreboard()

        assert matches == [
            TmLiveMatch(
                competition_code='bra.1',
                competition_name='Brasileirão',
                country='',
                country_flag_emoji='🇧🇷',
                home_team='Flamengo',
                away_team='Palmeiras',
                home_score=2,
                away_score=1,
                match_time="67'",
                status=MatchStatus.LIVE,
                match_id='401',
            )
        ]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('state', 'status_name', 'status', 'match_time'),
        [
            ('pre', 'STATUS_SCHEDULED', MatchStatus.NOT_STARTED, '16:30'),
            ('pre', 'STATUS_POSTPONED', MatchStatus.POSTPONED, '16:30'),
            ('in', 'STATUS_HALFTIME', MatchStatus.LIVE, 'Intervalo'),
            ('post', 'STATUS_FULL_TIME', MatchStatus.FINISHED, ''),
        ],
    )
    async def test_maps_status_and_brazilian_kickoff_time(
        self, scoreboard_route, state, status_name, status, match_time
    ):
        scoreboard_route.mock(return_value=_scoreboard(_event(state, status_name=status_name)))

        matches = await EspnService.fetch_scoreboard()

        assert (matches[0].status, matches[0].match_time) == (status, match_time)

    @pytest.mark.anyio
    async def test_scheduled_event_has_no_score(self, scoreboard_route):
        scoreboard_route.mock(return_value=_scoreboard(_event('pre')))

        matches = await EspnService.fetch_scoreboard()

        assert (matches[0].home_score, matches[0].away_score) == (None, None)

    @pytest.mark.anyio
    async def test_failing_league_is_skipped(self, scoreboard_route):
        scoreboard_route.mock(return_value=httpx.Response(500))

        matches = await EspnService.fetch_scoreboard()

        assert matches == []
