"""TheSportsDB client for team info and league standings."""

from typing import Any

import structlog

from bot.data.football import LeagueInfo
from bot.domain.models.football import SportsDBTeam, StandingRow
from bot.domain.services.team_name_matcher import TeamNameMatcher
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class TheSportsDBService:
    _BASE_URL = 'https://www.thesportsdb.com/api/v1/json/123'

    @classmethod
    async def get_teams(cls, league: LeagueInfo) -> list[SportsDBTeam]:
        resp = await HttpClient.get(
            f'{cls._BASE_URL}/search_all_teams.php',
            params={'l': league.sportsdb_name},
        )
        resp.raise_for_status()
        try:
            raw: list[dict[str, Any]] = resp.json().get('teams') or []
        except ValueError:
            return []
        return [cls._parse_team(t) for t in raw]

    @classmethod
    async def get_standings(cls, league: LeagueInfo) -> list[StandingRow]:
        resp = await HttpClient.get(
            f'{cls._BASE_URL}/lookuptable.php',
            params={'l': league.sportsdb_id, 's': league.sportsdb_season},
        )
        resp.raise_for_status()
        try:
            raw: list[dict[str, Any]] = resp.json().get('table') or []
        except ValueError:
            return []
        return [StandingRow(rank=int(r['intRank']), team=r['strTeam']) for r in raw]

    @classmethod
    async def search_team(cls, name: str) -> SportsDBTeam | None:
        resp = await HttpClient.get(
            f'{cls._BASE_URL}/searchteams.php',
            params={'t': name},
        )
        resp.raise_for_status()
        try:
            teams: list[dict[str, Any]] = resp.json().get('teams') or []
        except ValueError:
            return None
        if not teams:
            return None
        return cls._parse_team(teams[0])

    @staticmethod
    def find_best_match(tm_name: str, sports_teams: list[SportsDBTeam]) -> SportsDBTeam | None:
        by_name = {team.name: team for team in sports_teams}
        match = TeamNameMatcher.best(tm_name, list(by_name))
        return by_name[match] if match else None

    @staticmethod
    def _parse_team(t: dict) -> SportsDBTeam:
        return SportsDBTeam(
            name=t.get('strTeam', ''),
            country=t.get('strCountry', ''),
            founded=t.get('intFormedYear', ''),
            badge_url=t.get('strBadge', ''),
            team_id=t.get('idTeam', ''),
            stadium=t.get('strStadium', ''),
            capacity=t.get('intStadiumCapacity', ''),
        )
