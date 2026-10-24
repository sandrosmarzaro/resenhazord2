"""ESPN public soccer API — standings and scoreboards, reachable from datacenter IPs."""

from dataclasses import replace
from typing import Any, ClassVar

from bot.data.football import LeagueInfo
from bot.domain.models.football import TmStandingRow
from bot.infrastructure.http_client import HttpClient


class EspnService:
    _STANDINGS_URL: ClassVar[str] = (
        'https://site.api.espn.com/apis/v2/sports/soccer/{slug}/standings'
    )

    @classmethod
    async def fetch_standings(cls, league: LeagueInfo) -> list[TmStandingRow]:
        response = await HttpClient.get(cls._STANDINGS_URL.format(slug=league.espn_slug))
        response.raise_for_status()
        groups = [child['standings']['entries'] for child in response.json().get('children', [])]
        rows = [cls._parse_row(entry) for entries in groups for entry in entries]
        if len(groups) == 1:
            return sorted(rows, key=lambda row: row.rank)
        return cls._merge_groups(rows)

    @staticmethod
    def _parse_row(entry: dict[str, Any]) -> TmStandingRow:
        stats = {stat['name']: int(stat['value']) for stat in entry['stats'] if 'value' in stat}
        return TmStandingRow(
            rank=stats['rank'],
            team=entry['team']['displayName'],
            matches=stats['gamesPlayed'],
            wins=stats['wins'],
            draws=stats['ties'],
            losses=stats['losses'],
            goals_for=stats['pointsFor'],
            goals_against=stats['pointsAgainst'],
            goal_diff=stats['pointDifferential'],
            points=stats['points'],
        )

    @staticmethod
    def _merge_groups(rows: list[TmStandingRow]) -> list[TmStandingRow]:
        ordered = sorted(rows, key=lambda row: (-row.points, -row.goal_diff, -row.goals_for))
        return [replace(row, rank=position) for position, row in enumerate(ordered, start=1)]
