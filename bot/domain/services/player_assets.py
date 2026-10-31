"""Download lineup images (photos, badges, cards) in parallel."""

import contextlib
from collections.abc import Sequence

import anyio

from bot.infrastructure.http_client import HttpClient


class PlayerAssets:
    @staticmethod
    async def download(urls: Sequence[str]) -> list[bytes | None]:
        images: list[bytes | None] = [None] * len(urls)

        async def _get(i: int, url: str) -> None:
            with contextlib.suppress(Exception):
                images[i] = await HttpClient.get_buffer(url)

        async with anyio.create_task_group() as tg:
            for i, url in enumerate(urls):
                if url:
                    tg.start_soon(_get, i, url)

        return images
