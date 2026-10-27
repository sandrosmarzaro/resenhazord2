"""Best-rated players per position from the EA Sports FC ratings API, cached in memory."""

import asyncio
from datetime import UTC, datetime
from typing import Any, ClassVar

from bot.data.fifa_ratings import (
    FIFA_CARD_PREFIX,
    FIFA_MEN_GENDER,
    FIFA_PAGE_SIZE,
    FIFA_POSITION_IDS,
    FIFA_RATINGS_TTL,
    FIFA_RATINGS_URL,
)
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.football import FifaPlayer
from bot.infrastructure.http_client import HttpClient


class FifaRatings:
    _TTL: ClassVar = FIFA_RATINGS_TTL
    _cache: ClassVar[dict[str, tuple[datetime, list[FifaPlayer]]]] = {}

    @classmethod
    async def role_pools(cls, roles: set[str]) -> dict[str, list[FifaPlayer]]:
        ordered = sorted(roles)
        pools = await asyncio.gather(*(cls._players(role) for role in ordered))
        return dict(zip(ordered, pools, strict=True))

    @classmethod
    async def _players(cls, role: str) -> list[FifaPlayer]:
        cached = cls._cache.get(role)
        if cached and datetime.now(UTC) - cached[0] < cls._TTL:
            return cached[1]
        response = await HttpClient.get(
            FIFA_RATINGS_URL,
            params={
                'limit': FIFA_PAGE_SIZE,
                'offset': 0,
                'gender': FIFA_MEN_GENDER,
                'position': FIFA_POSITION_IDS[role],
                'locale': 'en',
            },
        )
        response.raise_for_status()
        players = [cls._player(item) for item in response.json()['items']]
        if not players:
            msg = 'Os ratings do EA FC não responderam agora. Tenta mais tarde! ⚽'
            raise ExternalServiceError(msg)
        cls._cache[role] = (datetime.now(UTC), players)
        return players

    @staticmethod
    def _player(item: dict[str, Any]) -> FifaPlayer:
        return FifaPlayer(
            name=item['commonName'] or f'{item["firstName"]} {item["lastName"]}',
            overall=item['overallRating'],
            card_url=_trusted(item['shieldUrl']),
        )


def _trusted(url: str) -> str:
    return url if url.startswith(FIFA_CARD_PREFIX) else ''
