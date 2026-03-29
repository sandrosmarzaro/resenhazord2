import random
from datetime import UTC, datetime
from typing import ClassVar

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient


class NhentaiScraper:
    MAX_PAGE = 100
    EXT_MAP: ClassVar[dict[str, str]] = {'j': 'jpg', 'p': 'png', 'g': 'gif', 'w': 'webp'}

    def __init__(self, mirror_url: str = 'https://nhentai.to') -> None:
        self._mirror_url = mirror_url

    async def fetch(self) -> HentaiGallery:
        page = random.randint(1, self.MAX_PAGE)  # noqa: S311
        res = await HttpClient.get(
            f'{self._mirror_url}/api/galleries/all',
            params={'page': page},
        )
        res.raise_for_status()
        results = res.json().get('result', [])

        if not results:
            msg = f'nhentai listing page {page} returned no galleries'
            raise ExternalServiceError(msg)

        return self._parse(random.choice(results))  # noqa: S311

    def _parse(self, data: dict) -> HentaiGallery:
        artists = [t['name'] for t in data['tags'] if t['type'] == 'artist']
        groups = [t['name'] for t in data['tags'] if t['type'] == 'group']
        tags = [t['name'] for t in data['tags'] if t['type'] == 'tag']
        lang_tag = next((t for t in data['tags'] if t['type'] == 'language'), None)
        type_tag = next((t for t in data['tags'] if t['type'] == 'category'), None)

        cover_ext = self.EXT_MAP.get(data['images']['cover']['t'], 'jpg')
        cover_url = f'https://t.nhentai.net/galleries/{data["media_id"]}/thumb.{cover_ext}'

        upload_ts = data.get('upload_date', 0)
        date_str = datetime.fromtimestamp(upload_ts, tz=UTC).strftime('%Y-%m') if upload_ts else ''

        return HentaiGallery(
            title=data['title'].get('english') or data['title'].get('pretty', ''),
            japanese_title=data['title'].get('japanese'),
            artists=artists,
            groups=groups,
            tags=tags,
            gallery_type=type_tag['name'] if type_tag else 'manga',
            language=lang_tag['name'] if lang_tag else 'unknown',
            pages=data.get('num_pages', 0),
            date=date_str,
            cover_url=cover_url,
            url=f'{self._mirror_url}/g/{data["id"]}/',
        )
