"""Football domain data types shared across services and commands."""

from dataclasses import dataclass
from enum import StrEnum


class MatchStatus(StrEnum):
    NOT_STARTED = 'notstarted'
    LIVE = 'live'
    FINISHED = 'finished'
    POSTPONED = 'postponed'
    HALF_TIME = 'halftime'


@dataclass(frozen=True)
class TmPlayer:
    name: str
    position: str
    age: int
    nationality: str
    club: str
    club_id: str
    market_value: str
    photo_url: str
    badge_url: str
    profile_url: str = ''
    nationality_flag_url: str = ''
    nationality_flag_emoji: str = ''


@dataclass(frozen=True)
class TmClub:
    rank: int
    name: str
    country: str
    squad_value: str
    club_id: str
    badge_url: str
    league_tm_id: str = ''


@dataclass(frozen=True)
class TmSquadStats:
    market_value: str
    squad_size: str
    avg_age: str
    foreigners_count: str
    foreigners_pct: str
    club_id: str = ''
    name: str = ''
    badge_url: str = ''


@dataclass(frozen=True)
class SportsDBTeam:
    name: str
    country: str
    founded: str
    badge_url: str
    team_id: str = ''
    stadium: str = ''
    capacity: str = ''


@dataclass(frozen=True)
class TmStandingRow:
    rank: int
    team: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int


@dataclass(frozen=True)
class StandingRow:
    rank: int
    team: str


@dataclass(frozen=True)
class TmLiveMatch:
    competition_code: str
    competition_name: str
    country: str
    country_flag_emoji: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    match_time: str
    status: MatchStatus
    match_id: str
    round: str | None = None
