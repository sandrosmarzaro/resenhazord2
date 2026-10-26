"""TheSportsDB lookup for club details (stadium, founding year)."""

from typing import Any

from bot.domain.models.football import SportsDBTeam
from bot.infrastructure.http_client import HttpClient


class TheSportsDBService:
    _BASE_URL = 'https://www.thesportsdb.com/api/v1/json/123'

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
