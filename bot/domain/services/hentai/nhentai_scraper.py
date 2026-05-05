import random
from datetime import UTC, datetime
from http import HTTPStatus
from typing import ClassVar

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient


class NhentaiScraper:
    MAX_PAGE = 100
    SEARCH_URL = '/api/galleries/search'
    EXT_MAP: ClassVar[dict[str, str]] = {'j': 'jpg', 'p': 'png', 'g': 'gif', 'w': 'webp'}

    def __init__(self, mirror_url: str = 'https://nhentai.to') -> None:
        self._mirror_url = mirror_url

    async def fetch(self) -> HentaiGallery:
        page = random.randint(1, self.MAX_PAGE)  # noqa: S311
        results = await self._fetch_page(page)
        if not results and page > 1:
            results = await self._fetch_page(1)

        if not results:
            msg = 'nhentai returned no galleries'
            raise ExternalServiceError(msg)

        return self._parse(random.choice(results))  # noqa: S311

    async def _fetch_page(self, page: int) -> list[dict]:
        res = await HttpClient.get(
            f'{self._mirror_url}{self.SEARCH_URL}',
            params={'query': '', 'page': page},
        )
        if res.status_code == HTTPStatus.NOT_FOUND:
            return []
        res.raise_for_status()
        return res.json().get('result', [])

    def _parse(self, data: dict) -> HentaiGallery:
        tags = data['tags']
        artists = self._filter_tags(tags, 'artist')
        groups = self._filter_tags(tags, 'group')
        tag_names = self._filter_tags(tags, 'tag')
        lang_tag = self._find_tag(tags, 'language')
        type_tag = self._find_tag(tags, 'category')

        cover_ext = self.EXT_MAP.get(data['images']['cover']['t'], 'jpg')
        cover_url = f'https://t.nhentai.net/galleries/{data["media_id"]}/thumb.{cover_ext}'

        upload_ts = data.get('upload_date', 0)
        date_str = datetime.fromtimestamp(upload_ts, tz=UTC).strftime('%Y-%m') if upload_ts else ''

        return HentaiGallery(
            title=data['title'].get('english') or data['title'].get('pretty', ''),
            japanese_title=data['title'].get('japanese'),
            artists=artists,
            groups=groups,
            tags=tag_names,
            gallery_type=type_tag['name'] if type_tag else 'manga',
            language=lang_tag['name'] if lang_tag else 'unknown',
            pages=data.get('num_pages', 0),
            date=date_str,
            cover_url=cover_url,
            url=f'{self._mirror_url}/g/{data["id"]}/',
        )

    @staticmethod
    def _filter_tags(tags: list[dict], tag_type: str) -> list[str]:
        return [t['name'] for t in tags if t['type'] == tag_type]

    @staticmethod
    def _find_tag(tags: list[dict], tag_type: str) -> dict | None:
        return next((t for t in tags if t['type'] == tag_type), None)
