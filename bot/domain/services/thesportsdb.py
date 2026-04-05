"""TheSportsDB client for team info and league standings."""

from dataclasses import dataclass

import structlog

from bot.data.football import LeagueInfo
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

BASE_URL = 'https://www.thesportsdb.com/api/v1/json/3'


@dataclass(frozen=True)
class SportsDBTeam:
    name: str
    country: str
    founded: str
    badge_url: str


@dataclass(frozen=True)
class StandingRow:
    rank: int
    team: str


class TheSportsDBService:
    @classmethod
    async def get_teams(cls, league: LeagueInfo) -> list[SportsDBTeam]:
        resp = await HttpClient.get(
            f'{BASE_URL}/search_all_teams.php',
            params={'l': league.sportsdb_name},
        )
        resp.raise_for_status()
        raw = resp.json().get('teams') or []
        return [cls._parse_team(t) for t in raw]

    @classmethod
    async def get_standings(cls, league: LeagueInfo) -> list[StandingRow]:
        resp = await HttpClient.get(
            f'{BASE_URL}/lookuptable.php',
            params={'l': league.sportsdb_id, 's': league.sportsdb_season},
        )
        resp.raise_for_status()
        raw = resp.json().get('table') or []
        return [
            StandingRow(rank=int(r['intRank']), team=r['strTeam'])
            for r in raw
        ]

    @staticmethod
    def _parse_team(t: dict) -> SportsDBTeam:
        return SportsDBTeam(
            name=t.get('strTeam', ''),
            country=t.get('strCountry', ''),
            founded=t.get('intFormedYear', ''),
            badge_url=t.get('strBadge', ''),
        )
