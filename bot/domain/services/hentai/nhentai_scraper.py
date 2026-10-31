import random
from datetime import UTC, datetime
from typing import ClassVar

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient


class NhentaiScraper:
    MAX_PAGE = 100
    SITE_URL = 'https://nhentai.net'
    SEARCH_URL = SITE_URL + '/api/v2/search'
    GALLERY_URL = SITE_URL + '/api/v2/galleries/{id}'
    COVER_DOMAIN = 'https://t.nhentai.net'
    SEARCH_QUERY = '-lolicon -shotacon'
    # The API docs ask for a User-Agent that identifies the app.
    HEADERS: ClassVar[dict[str, str]] = {
        'User-Agent': 'Resenhazord2 (https://github.com/sandrosmarzaro/resenhazord2)'
    }
    UNTRANSLATED_LANGUAGE_TAG = 'translated'

    @classmethod
    async def fetch(cls) -> HentaiGallery:
        page = random.randint(1, cls.MAX_PAGE)
        results = await cls._search(page)
        if not results and page > 1:
            results = await cls._search(1)

        if not results:
            msg = 'nhentai returned no galleries'
            raise ExternalServiceError(msg)

        response = await HttpClient.get(
            cls.GALLERY_URL.format(id=random.choice(results)['id']), headers=cls.HEADERS
        )
        response.raise_for_status()
        return cls._parse(response.json())

    @classmethod
    async def _search(cls, page: int) -> list[dict]:
        response = await HttpClient.get(
            cls.SEARCH_URL,
            params={'query': cls.SEARCH_QUERY, 'page': page},
            headers=cls.HEADERS,
        )
        response.raise_for_status()
        return response.json().get('result', [])

    @classmethod
    def _parse(cls, data: dict) -> HentaiGallery:
        tags = data['tags']
        languages = [
            name
            for name in cls._filter_tags(tags, 'language')
            if name != cls.UNTRANSLATED_LANGUAGE_TAG
        ]
        categories = cls._filter_tags(tags, 'category')
        title = data['title']

        return HentaiGallery(
            title=title.get('english') or title.get('pretty', ''),
            japanese_title=title.get('japanese'),
            artists=cls._filter_tags(tags, 'artist'),
            groups=cls._filter_tags(tags, 'group'),
            tags=cls._filter_tags(tags, 'tag'),
            gallery_type=categories[0] if categories else 'manga',
            language=languages[0] if languages else 'unknown',
            pages=data.get('num_pages', 0),
            date=datetime.fromtimestamp(data['upload_date'], tz=UTC).strftime('%Y-%m'),
            cover_url=f'{cls.COVER_DOMAIN}/{data["cover"]["path"]}',
            url=f'{cls.SITE_URL}/g/{data["id"]}/',
        )

    @staticmethod
    def _filter_tags(tags: list[dict], tag_type: str) -> list[str]:
        return [t['name'] for t in tags if t['type'] == tag_type]
