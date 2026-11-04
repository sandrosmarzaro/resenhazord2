from dataclasses import dataclass
from typing import Any

from bot.infrastructure.http_client import HttpClient


@dataclass(frozen=True)
class WikiPage:
    title: str
    thumbnail: str | None


class WikimediaClient:
    WIKIPEDIA_API = 'https://en.wikipedia.org/w/api.php'
    COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
    USER_AGENT = 'ResenhazordBot/2.0 (https://github.com/sandrosmarzaro/resenhazord2)'
    SEARCH_TIMEOUT = 8.0
    DOWNLOAD_TIMEOUT = 12.0
    THUMBNAIL_SIZE = 640
    FILE_NAMESPACE = 6

    @classmethod
    async def search_wikipedia(cls, search: str) -> WikiPage:
        return await cls._first_page(cls.WIKIPEDIA_API, {'gsrsearch': search})

    @classmethod
    async def search_commons_files(cls, search: str) -> WikiPage:
        params = {'gsrsearch': search, 'gsrnamespace': str(cls.FILE_NAMESPACE)}
        return await cls._first_page(cls.COMMONS_API, params)

    @classmethod
    async def download(cls, url: str) -> bytes:
        return await HttpClient.get_buffer(
            url, timeout=cls.DOWNLOAD_TIMEOUT, headers={'User-Agent': cls.USER_AGENT}
        )

    @classmethod
    async def _first_page(cls, api: str, search_params: dict[str, str]) -> WikiPage:
        params = {
            'action': 'query',
            'generator': 'search',
            **search_params,
            'gsrlimit': '1',
            'prop': 'pageimages',
            'pithumbsize': str(cls.THUMBNAIL_SIZE),
            'format': 'json',
        }
        response = await HttpClient.get(
            api, params=params, timeout=cls.SEARCH_TIMEOUT, headers={'User-Agent': cls.USER_AGENT}
        )
        data = response.json()
        pages: dict[str, Any] = (data.get('query') or {}).get('pages') or {}
        first: dict[str, Any] = next(iter(pages.values()), {})
        return WikiPage(
            title=first.get('title', ''),
            thumbnail=(first.get('thumbnail') or {}).get('source'),
        )
