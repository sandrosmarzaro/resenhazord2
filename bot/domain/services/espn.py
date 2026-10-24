"""ESPN public soccer API — standings and scoreboards, reachable from datacenter IPs."""

import asyncio
from dataclasses import replace
from datetime import datetime
from typing import Any, ClassVar

import structlog

from bot.data.espn_leagues import SCOREBOARD_LEAGUES, ScoreboardLeague
from bot.data.football import BR_TIMEZONE, LeagueInfo
from bot.domain.models.football import MatchStatus, TmLiveMatch, TmStandingRow
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class EspnService:
    _STANDINGS_URL: ClassVar[str] = (
        'https://site.api.espn.com/apis/v2/sports/soccer/{slug}/standings'
    )

    _SCOREBOARD_URL: ClassVar[str] = (
        'https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard'
    )
    _STATES: ClassVar[dict[str, MatchStatus]] = {
        'pre': MatchStatus.NOT_STARTED,
        'in': MatchStatus.LIVE,
        'post': MatchStatus.FINISHED,
    }
    _POSTPONED: ClassVar[str] = 'STATUS_POSTPONED'
    _HALFTIME: ClassVar[str] = 'STATUS_HALFTIME'
    _HALFTIME_LABEL: ClassVar[str] = 'Intervalo'

    @classmethod
    async def fetch_scoreboard(cls) -> list[TmLiveMatch]:
        batches = await asyncio.gather(
            *(cls._fetch_league_scoreboard(league) for league in SCOREBOARD_LEAGUES),
            return_exceptions=True,
        )
        matches: list[TmLiveMatch] = []
        for league, batch in zip(SCOREBOARD_LEAGUES, batches, strict=True):
            if isinstance(batch, BaseException):
                logger.warning('espn_scoreboard_failed', league=league.slug, error=str(batch))
                continue
            matches.extend(batch)
        return matches

    @classmethod
    async def _fetch_league_scoreboard(cls, league: ScoreboardLeague) -> list[TmLiveMatch]:
        response = await HttpClient.get(cls._SCOREBOARD_URL.format(slug=league.slug))
        response.raise_for_status()
        return [cls._parse_event(event, league) for event in response.json().get('events', [])]

    @classmethod
    def _parse_event(cls, event: dict[str, Any], league: ScoreboardLeague) -> TmLiveMatch:
        competition = event['competitions'][0]
        sides = {side['homeAway']: side for side in competition['competitors']}
        status = cls._status(competition['status'])
        started = status in {MatchStatus.LIVE, MatchStatus.FINISHED}
        return TmLiveMatch(
            competition_code=league.slug,
            competition_name=league.name,
            country='',
            country_flag_emoji=league.flag,
            home_team=sides['home']['team']['shortDisplayName'],
            away_team=sides['away']['team']['shortDisplayName'],
            home_score=int(sides['home']['score']) if started else None,
            away_score=int(sides['away']['score']) if started else None,
            match_time=cls._match_time(event['date'], competition['status'], status),
            status=status,
            match_id=event['id'],
        )

    @classmethod
    def _status(cls, status: dict[str, Any]) -> MatchStatus:
        if status['type']['name'] == cls._POSTPONED:
            return MatchStatus.POSTPONED
        return cls._STATES[status['type']['state']]

    @classmethod
    def _match_time(cls, kickoff: str, status: dict[str, Any], match_status: MatchStatus) -> str:
        if match_status == MatchStatus.FINISHED:
            return ''
        if match_status != MatchStatus.LIVE:
            kickoff_utc = datetime.fromisoformat(kickoff)
            return kickoff_utc.astimezone(BR_TIMEZONE).strftime('%H:%M')
        if status['type']['name'] == cls._HALFTIME:
            return cls._HALFTIME_LABEL
        return status['displayClock']

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
