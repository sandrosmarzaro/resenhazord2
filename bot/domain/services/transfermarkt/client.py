"""Transfermarkt HTTP client — all async fetch operations."""

import asyncio
from http import HTTPStatus
from typing import ClassVar

import httpx
import structlog

from bot.data.football import LeagueInfo
from bot.data.transfermarkt_positions import POSITION_FILTERS
from bot.data.transfermarkt_urls import (
    CLUB_SQUAD_URL,
    CLUBS_URL,
    DEFAULT_SEASON,
    GLOBAL_MAX_PAGES,
    GLOBAL_URL,
    HEADERS,
    LEAGUE_MAX_PAGES,
    LEAGUE_URL,
    PLAYERS_PER_PAGE,
    POSITION_FILTER_URL,
    POSITION_MAX_PAGES,
    SQUAD_VALUES_URL,
)
from bot.domain.exceptions import TransfermarktBlockedError
from bot.domain.models.football import TmClub, TmPlayer, TmSquadStats
from bot.domain.services.transfermarkt.parser import TransfermarktParser
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class TransfermarktClient:
    HEADERS = HEADERS
    PLAYERS_PER_PAGE = PLAYERS_PER_PAGE
    GLOBAL_MAX_PAGES = GLOBAL_MAX_PAGES
    LEAGUE_MAX_PAGES = LEAGUE_MAX_PAGES
    POSITION_MAX_PAGES = POSITION_MAX_PAGES
    MAX_CONCURRENT_REQUESTS = 8
    WAF_ACTION_HEADER = 'x-amzn-waf-action'
    _semaphore: ClassVar[asyncio.Semaphore | None] = None

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(cls.MAX_CONCURRENT_REQUESTS)
        return cls._semaphore

    @classmethod
    async def _get(cls, url: str, **kwargs) -> httpx.Response:
        async with cls._get_semaphore():
            response = await HttpClient.get(url, **kwargs)
        if response.status_code == HTTPStatus.ACCEPTED or cls.WAF_ACTION_HEADER in response.headers:
            logger.warning('transfermarkt_blocked', url=url, status=response.status_code)
            raise TransfermarktBlockedError
        return response

    @staticmethod
    def _raise_if_blocked(batches: list) -> None:
        blocked = next((b for b in batches if isinstance(b, TransfermarktBlockedError)), None)
        if blocked is not None:
            raise blocked

    @classmethod
    async def fetch_page(cls, page: int, league: LeagueInfo | None = None) -> list[TmPlayer]:
        if league:
            url = LEAGUE_URL.format(slug=league.tm_slug, tm_id=league.tm_id, page=page)
        else:
            url = f'{GLOBAL_URL}?page={page}'
        response = await cls._get(url, headers=HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_page(response.text)

    @classmethod
    async def fetch_by_specific_position(
        cls, role: str, max_pages: int | None = None
    ) -> list[TmPlayer]:
        mapping = POSITION_FILTERS.get(role)
        if not mapping:
            return []
        ausrichtung, pos_ids = mapping
        pages = max_pages if max_pages is not None else POSITION_MAX_PAGES

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
            response = await cls._get(POSITION_FILTER_URL, params=params, headers=HEADERS)
            response.raise_for_status()
            return TransfermarktParser.parse_page(response.text)

        tasks = [_one(pid, page) for pid in pos_ids for page in range(1, pages + 1)]
        batches = await asyncio.gather(*tasks, return_exceptions=True)
        cls._raise_if_blocked(batches)
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

    @classmethod
    async def fetch_player_profile(cls, profile_url: str) -> dict[str, str]:
        response = await cls._get(profile_url, headers=HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_player_profile(response.text)

    @classmethod
    async def fetch_squad_values(cls, league: LeagueInfo) -> dict[str, TmSquadStats]:
        url = SQUAD_VALUES_URL.format(slug=league.tm_slug, tm_id=league.tm_id)
        response = await cls._get(url, headers=HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_squad_values(response.text)

    @classmethod
    async def fetch_standings(cls, league: LeagueInfo) -> dict[str, int]:
        url = f'{TransfermarktParser.TM_BASE}/{league.tm_slug}/tabelle/wettbewerb/{league.tm_id}'
        response = await cls._get(url, headers=HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_tabelle(response.text)

    @classmethod
    async def fetch_top_clubs(cls, count: int) -> list[TmClub]:
        response = await cls._get(CLUBS_URL, headers=HEADERS)
        response.raise_for_status()
        return TransfermarktParser.parse_clubs_page(response.text)[:count]

    @classmethod
    async def fetch_league_full_squad(cls, league: LeagueInfo) -> list[TmPlayer]:
        url = SQUAD_VALUES_URL.format(slug=league.tm_slug, tm_id=league.tm_id)
        response = await cls._get(url, headers=HEADERS)
        response.raise_for_status()
        clubs = TransfermarktParser.parse_league_clubs(response.text)
        if not clubs:
            return []

        async def _one(club: TmClub) -> list[TmPlayer]:
            squad_url = CLUB_SQUAD_URL.format(club_id=club.club_id, season=DEFAULT_SEASON)
            r = await cls._get(squad_url, headers=HEADERS)
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
        cls._raise_if_blocked(batches)
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
