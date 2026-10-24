import httpx
import pytest

from bot.data.football import LEAGUES
from bot.domain.models.football import TmStandingRow
from bot.domain.services.espn import EspnService

_STANDINGS_URL = 'https://site.api.espn.com/apis/v2/sports/soccer/bra.1/standings'


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
