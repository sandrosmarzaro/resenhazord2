"""HTML parsing for Transfermarkt pages — public facade."""

import structlog

from bot.domain.models.football import (
    TmClub,
    TmLiveMatch,
    TmPlayer,
    TmSquadStats,
    TmStandingRow,
)
from bot.domain.services.transfermarkt.club_parser import ClubParser
from bot.domain.services.transfermarkt.live_parser import LiveMatchParser
from bot.domain.services.transfermarkt.player_parser import PlayerParser
from bot.domain.services.transfermarkt.row_parser import RowParser
from bot.domain.services.transfermarkt.squad_value_parser import SquadValueParser
from bot.domain.services.transfermarkt.standing_parser import StandingParser

logger = structlog.get_logger()


class TransfermarktParser:
    TM_BASE = 'https://www.transfermarkt.com.br'
    BADGE_CDN = 'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png'

    @classmethod
    def parse_page(cls, html: str, *, require_club: bool = True) -> list[TmPlayer]:
        return PlayerParser.parse_page(html, require_club=require_club)

    @classmethod
    def parse_squad_values(cls, html: str) -> dict[str, TmSquadStats]:
        return SquadValueParser.parse_squad_values(html)

    @classmethod
    def parse_tabelle(cls, html: str) -> dict[str, int]:
        return StandingParser.parse_tabelle(html)

    @classmethod
    def parse_full_tabelle(cls, html: str) -> list[TmStandingRow]:
        return StandingParser.parse_full_tabelle(html)

    @classmethod
    def parse_clubs_page(cls, html: str) -> list[TmClub]:
        return ClubParser.parse_clubs_page(html)

    @classmethod
    def parse_league_clubs(cls, html: str) -> list[TmClub]:
        return ClubParser.parse_league_clubs(html)

    @classmethod
    def parse_live_matches(cls, html: str) -> list[TmLiveMatch]:
        return LiveMatchParser.parse_live_matches(html)

    @classmethod
    def parse_player_profile(cls, html: str) -> dict[str, str]:
        return RowParser.parse_player_profile(html)
