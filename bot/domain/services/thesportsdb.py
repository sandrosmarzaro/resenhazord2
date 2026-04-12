"""TheSportsDB client for team info and league standings."""

import difflib

import structlog

from bot.data.football import LeagueInfo
from bot.data.football_team_prefixes import CLUB_PREFIXES
from bot.domain.models.football import SportsDBTeam, StandingRow
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

BASE_URL = 'https://www.thesportsdb.com/api/v1/json/3'

_MATCH_MIN_JACCARD = 0.25
_SUBSTRING_MIN_LEN = 4


class TheSportsDBService:
    @classmethod
    async def get_teams(cls, league: LeagueInfo) -> list[SportsDBTeam]:
        resp = await HttpClient.get(
            f'{BASE_URL}/search_all_teams.php',
            params={'l': league.sportsdb_name},
        )
        resp.raise_for_status()
        try:
            raw = resp.json().get('teams') or []
        except ValueError:
            return []
        return [cls._parse_team(t) for t in raw]

    @classmethod
    async def get_standings(cls, league: LeagueInfo) -> list[StandingRow]:
        resp = await HttpClient.get(
            f'{BASE_URL}/lookuptable.php',
            params={'l': league.sportsdb_id, 's': league.sportsdb_season},
        )
        resp.raise_for_status()
        try:
            raw = resp.json().get('table') or []
        except ValueError:
            return []
        return [StandingRow(rank=int(r['intRank']), team=r['strTeam']) for r in raw]

    @classmethod
    async def search_team(cls, name: str) -> SportsDBTeam | None:
        resp = await HttpClient.get(
            f'{BASE_URL}/searchteams.php',
            params={'t': name},
        )
        resp.raise_for_status()
        try:
            teams = resp.json().get('teams') or []
        except ValueError:
            return None
        if not teams:
            return None
        return cls._parse_team(teams[0])

    @classmethod
    def find_best_match(cls, tm_name: str, sports_teams: list[SportsDBTeam]) -> SportsDBTeam | None:
        """Best-effort match of a TM club name against SportsDB teams for enrichment."""
        if not sports_teams:
            return None
        tm_tokens = cls._name_tokens(tm_name)
        if not tm_tokens:
            return None
        best: SportsDBTeam | None = None
        best_jaccard = 0.0
        best_ratio = 0.0
        for t in sports_teams:
            t_tokens = cls._name_tokens(t.name)
            if not t_tokens:
                continue
            union = len(tm_tokens | t_tokens)
            jaccard = len(tm_tokens & t_tokens) / union if union else 0.0
            if jaccard == 0 and cls._token_substring_hit(tm_tokens, t_tokens):
                jaccard = _MATCH_MIN_JACCARD
            ratio = difflib.SequenceMatcher(None, tm_name.lower(), t.name.lower()).ratio()
            if jaccard > best_jaccard or (jaccard == best_jaccard and ratio > best_ratio):
                best = t
                best_jaccard = jaccard
                best_ratio = ratio
        if best_jaccard < _MATCH_MIN_JACCARD:
            return None
        return best

    @staticmethod
    def _name_tokens(name: str) -> set[str]:
        raw = name.lower().replace('.', ' ').replace('-', ' ')
        tokens = {t for t in raw.split() if t}
        filtered = tokens - CLUB_PREFIXES
        return filtered or tokens

    @staticmethod
    def _token_substring_hit(tm_tokens: set[str], t_tokens: set[str]) -> bool:
        for a in tm_tokens:
            if len(a) < _SUBSTRING_MIN_LEN:
                continue
            for b in t_tokens:
                if len(b) < _SUBSTRING_MIN_LEN:
                    continue
                if a.startswith(b) or b.startswith(a):
                    return True
        return False

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
