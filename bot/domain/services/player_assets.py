"""Fetch player photos and badges in parallel."""

import contextlib

import anyio

from bot.domain.models.football import TmPlayer
from bot.domain.services.transfermarkt.service import TransfermarktService
from bot.infrastructure.http_client import HttpClient


class PlayerAssets:
    @staticmethod
    async def fetch(
        ordered: list[TmPlayer | None],
    ) -> tuple[list[bytes | None], list[bytes | None]]:
        n = len(ordered)
        photos: list[bytes | None] = [None] * n
        badges: list[bytes | None] = [None] * n

        async def _get(url: str) -> bytes | None:
            with contextlib.suppress(Exception):
                return await HttpClient.get_buffer(url, headers=TransfermarktService.HEADERS)
            return None

        async def _fetch_player(i: int, player: TmPlayer) -> None:
            if player.photo_url:
                photos[i] = await _get(player.photo_url)
            if player.badge_url:
                badges[i] = await _get(player.badge_url)

        async with anyio.create_task_group() as tg:
            for i, player in enumerate(ordered):
                if player:
                    tg.start_soon(_fetch_player, i, player)

        return photos, badges
