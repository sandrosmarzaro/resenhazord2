"""Football domain data types shared across services and commands."""

from dataclasses import dataclass


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
class StandingRow:
    rank: int
    team: str
