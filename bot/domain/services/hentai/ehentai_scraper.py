import html
import random
import re
from collections import defaultdict
from datetime import UTC, datetime
from re import Pattern
from typing import ClassVar

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient


class EHentaiScraper:
    SITE_URL = 'https://e-hentai.org'
    API_URL = 'https://api.e-hentai.org/api.php'
    # A bitmask of the categories to hide. Leaves doujinshi, manga, artist CG and game CG,
    # since the others hold real people and non-H.
    HIDDEN_CATEGORIES = 993
    SEARCH_QUERY = '-"female:lolicon$" -"male:shotacon$"'
    # The listing has no random order, so a random gallery id is the page cursor. Both
    # bounds sit inside the id range (past 4.29M in 2026), and it only ever grows.
    MIN_CURSOR = 100_000
    MAX_CURSOR = 4_000_000
    UNTRANSLATED_LANGUAGE_TAG = 'translated'
    TAG_NAMESPACES: ClassVar[tuple[str, ...]] = ('female', 'male', 'mixed', 'other')
    _GALLERY_LINK: ClassVar[Pattern[str]] = re.compile(r'e-hentai\.org/g/(\d+)/([0-9a-f]+)/')

    @classmethod
    async def fetch(cls) -> HentaiGallery:
        response = await HttpClient.get(
            f'{cls.SITE_URL}/',
            params={
                'f_cats': cls.HIDDEN_CATEGORIES,
                'f_search': cls.SEARCH_QUERY,
                'next': random.randint(cls.MIN_CURSOR, cls.MAX_CURSOR),
            },
        )
        response.raise_for_status()
        # A temporary IP ban also answers 200, with no galleries in the page.
        galleries = sorted(set(cls._GALLERY_LINK.findall(response.text)))
        if not galleries:
            msg = 'E-Hentai returned no galleries'
            raise ExternalServiceError(msg)

        gallery_id, token = random.choice(galleries)
        return await cls._retrieve_gallery(int(gallery_id), token)

    @classmethod
    async def _retrieve_gallery(cls, gallery_id: int, token: str) -> HentaiGallery:
        response = await HttpClient.post(
            cls.API_URL,
            json={'method': 'gdata', 'gidlist': [[gallery_id, token]], 'namespace': 1},
        )
        response.raise_for_status()
        return cls._parse(response.json()['gmetadata'][0])

    @classmethod
    def _parse(cls, data: dict) -> HentaiGallery:
        tags = cls._by_namespace(data['tags'])
        languages = [name for name in tags['language'] if name != cls.UNTRANSLATED_LANGUAGE_TAG]
        posted = datetime.fromtimestamp(int(data['posted']), tz=UTC)

        return HentaiGallery(
            title=html.unescape(data['title']),
            japanese_title=html.unescape(data['title_jpn']) or None,
            artists=tags['artist'],
            groups=tags['group'],
            tags=[name for namespace in cls.TAG_NAMESPACES for name in tags[namespace]],
            gallery_type=data['category'].lower(),
            language=languages[0] if languages else 'unknown',
            pages=int(data['filecount']),
            date=posted.strftime('%Y-%m'),
            cover_url=data['thumb'],
            url=f'{cls.SITE_URL}/g/{data["gid"]}/{data["token"]}/',
        )

    @staticmethod
    def _by_namespace(tags: list[str]) -> defaultdict[str, list[str]]:
        names: defaultdict[str, list[str]] = defaultdict(list)
        for tag in tags:
            namespace, _, name = tag.partition(':')
            names[namespace].append(name)
        return names
