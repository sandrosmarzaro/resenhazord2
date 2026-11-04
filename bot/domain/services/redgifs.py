import random
from http import HTTPStatus
from typing import Any

import httpx

from bot.data.nsfw_tags import MINOR_TAG_TERMS
from bot.data.redgifs_media import RedGifsMedia
from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient


class RedGifs:
    """Draws one trending item for a tag, with a temporary token that needs no account.

    It drops items whose tags or niches point to minors. That is a denylist over tags people
    write, so it reduces the risk and can't rule it out."""

    API_URL = 'https://api.redgifs.com/v2'
    REQUEST_TIMEOUT_SECONDS = 30.0
    PAGE_SIZE = 40
    # Deeper trending pages drift away from the tag.
    MAX_PAGE = 10
    VIDEO_TYPE = 1
    VIDEOS_ONLY = 'g'

    def __init__(self) -> None:
        self._token: str | None = None

    async def random_media(self, tag: str, *, video_only: bool = False) -> RedGifsMedia:
        params = {
            'tags': tag,
            'order': 'trending',
            'count': self.PAGE_SIZE,
            'page': random.randint(1, self.MAX_PAGE),
        }
        if video_only:
            params['type'] = self.VIDEOS_ONLY
        safe = [item for item in await self._search(params) if not self._points_to_minors(item)]
        if not safe:
            msg = 'Não achei nada nessa categoria agora, tenta de novo'
            raise ExternalServiceError(msg)
        item = random.choice(safe)
        return RedGifsMedia(url=item['urls']['sd'], is_video=item['type'] == self.VIDEO_TYPE)

    async def _search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        response = await self._get_search(params)
        # The temporary token lasts a day.
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            self._token = None
            response = await self._get_search(params)
        response.raise_for_status()
        return response.json()['gifs']

    async def _get_search(self, params: dict[str, Any]) -> httpx.Response:
        token = self._token or await self._fetch_token()
        return await HttpClient.get(
            f'{self.API_URL}/gifs/search',
            params=params,
            headers={'Authorization': f'Bearer {token}'},
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )

    async def _fetch_token(self) -> str:
        response = await HttpClient.get(
            f'{self.API_URL}/auth/temporary', timeout=self.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        self._token = response.json()['token']
        return self._token

    @staticmethod
    def _points_to_minors(item: dict[str, Any]) -> bool:
        labels = [*item.get('tags', []), *item.get('niches', [])]
        return any(term in label.lower() for label in labels for term in MINOR_TAG_TERMS)
