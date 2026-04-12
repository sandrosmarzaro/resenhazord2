"""Transfermarkt HTTP client — all async fetch operations."""

import asyncio
from typing import ClassVar

import structlog

from bot.data.football import LeagueInfo
from bot.domain.models.football import TmClub, TmPlayer, TmSquadStats
from bot.domain.services.transfermarkt.parser import TransfermarktParser
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class TransfermarktClient:
    GLOBAL_URL = (
        'https://www.transfermarkt.com.br/spieler-statistik/wertvollstespieler/marktwertetop'
    )
    POSITION_FILTER_URL = (
        'https://www.transfermarkt.com.br/spieler-statistik/wertvollstespieler/'
        'marktwertetop/plus/0/galerie/0'
    )
    CLUBS_URL = (
        'https://www.transfermarkt.com.br/spieler-statistik/wertvollstemannschaften/marktwertetop'
    )
    LEAGUE_URL = 'https://www.transfermarkt.com.br/{slug}/marktwerte/wettbewerb/{tm_id}/page/{page}'
    SQUAD_VALUES_URL = 'https://www.transfermarkt.com.br/{slug}/startseite/wettbewerb/{tm_id}'
    CLUB_SQUAD_URL = (
        'https://www.transfermarkt.com.br/club/kader/verein/{club_id}/saison_id/{season}/plus/1'
    )
    DEFAULT_SEASON = '2025'
    HEADERS: ClassVar[dict[str, str]] = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://www.transfermarkt.com.br/',
    }
    PLAYERS_PER_PAGE = 25
    GLOBAL_MAX_PAGES = 40
    LEAGUE_MAX_PAGES = 4
    POSITION_MAX_PAGES = 4

    POSITION_FILTERS: ClassVar[dict[str, tuple[str, tuple[int, ...]]]] = {
        'GK': ('Torwart', (1,)),
        'CB': ('Abwehr', (3,)),
        'LB': ('Abwehr', (4,)),
        'RB': ('Abwehr', (5,)),
        'DM': ('Mittelfeld', (6,)),
        'CM': ('Mittelfeld', (7, 8, 9)),
        'AM': ('Mittelfeld', (10,)),
        'LW': ('Sturm', (11,)),
        'RW': ('Sturm', (12,)),
        'ST': ('Sturm', (13, 14)),
    }

    @classmethod
    async def fetch_page(cls, page: int, league: LeagueInfo | None = None) -> list[TmPlayer]:
        if league:
            url = cls.LEAGUE_URL.format(slug=league.tm_slug, tm_id=league.tm_id, page=page)
        else:
            url = f'{cls.GLOBAL_URL}?page={page}'
        response = await HttpClient.get(url, headers=cls.HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_page(response.text)

    @classmethod
    async def fetch_by_specific_position(
        cls, role: str, max_pages: int | None = None
    ) -> list[TmPlayer]:
        mapping = cls.POSITION_FILTERS.get(role)
        if not mapping:
            return []
        ausrichtung, pos_ids = mapping
        pages = max_pages if max_pages is not None else cls.POSITION_MAX_PAGES

        async def _one(pos_id: int, page: int) -> list[TmPlayer]:
            params = {
                'ausrichtung': ausrichtung,
                'spielerposition_id': str(pos_id),
                'altersklasse': 'alle',
                'jahrgang': '0',
                'land_id': '0',
                'kontinent_id': '0',
                'jahr': '0',
                'page': str(page),
            }
            response = await HttpClient.get(
                cls.POSITION_FILTER_URL, params=params, headers=cls.HEADERS
            )
            response.raise_for_status()
            return TransfermarktParser.parse_page(response.text)

        tasks = [_one(pid, page) for pid in pos_ids for page in range(1, pages + 1)]
        batches = await asyncio.gather(*tasks)
        seen: set[str] = set()
        merged: list[TmPlayer] = []
        for batch in batches:
            for p in batch:
                if p.name not in seen:
                    seen.add(p.name)
                    merged.append(p)
        return merged

    @classmethod
    async def fetch_player_profile(cls, profile_url: str) -> dict[str, str]:
        response = await HttpClient.get(profile_url, headers=cls.HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_player_profile(response.text)

    @classmethod
    async def fetch_squad_values(cls, league: LeagueInfo) -> dict[str, TmSquadStats]:
        url = cls.SQUAD_VALUES_URL.format(slug=league.tm_slug, tm_id=league.tm_id)
        response = await HttpClient.get(url, headers=cls.HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_squad_values(response.text)

    @classmethod
    async def fetch_standings(cls, league: LeagueInfo) -> dict[str, int]:
        url = f'{TransfermarktParser.TM_BASE}/{league.tm_slug}/tabelle/wettbewerb/{league.tm_id}'
        response = await HttpClient.get(url, headers=cls.HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_tabelle(response.text)

    @classmethod
    async def fetch_top_clubs(cls, count: int) -> list[TmClub]:
        response = await HttpClient.get(cls.CLUBS_URL, headers=cls.HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_clubs_page(response.text)[:count]

    @classmethod
    async def fetch_league_full_squad(cls, league: LeagueInfo) -> list[TmPlayer]:
        url = cls.SQUAD_VALUES_URL.format(slug=league.tm_slug, tm_id=league.tm_id)
        response = await HttpClient.get(url, headers=cls.HEADERS)
        response.raise_for_status()
        clubs = TransfermarktParser.parse_league_clubs(response.text)
        if not clubs:
            return []

        async def _one(club: TmClub) -> list[TmPlayer]:
            squad_url = cls.CLUB_SQUAD_URL.format(club_id=club.club_id, season=cls.DEFAULT_SEASON)
            r = await HttpClient.get(squad_url, headers=cls.HEADERS)
            r.raise_for_status()
            players = TransfermarktParser.parse_page(r.text, require_club=False)
            return [
                TmPlayer(
                    name=p.name,
                    position=p.position,
                    age=p.age,
                    nationality=p.nationality,
                    club=club.name,
                    club_id=club.club_id,
                    market_value=p.market_value,
                    photo_url=p.photo_url,
                    badge_url=club.badge_url,
                    profile_url=p.profile_url,
                    nationality_flag_url=p.nationality_flag_url,
                    nationality_flag_emoji=p.nationality_flag_emoji,
                )
                for p in players
            ]

        batches = await asyncio.gather(*[_one(c) for c in clubs], return_exceptions=True)
        seen: set[str] = set()
        merged: list[TmPlayer] = []
        for batch in batches:
            if isinstance(batch, BaseException):
                continue
            for p in batch:
                if p.name not in seen:
                    seen.add(p.name)
                    merged.append(p)
        return merged
