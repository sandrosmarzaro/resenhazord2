import json
import random
import struct
from datetime import UTC, datetime
from http import HTTPStatus
from typing import ClassVar

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient


class HitomiScraper:
    RESOURCE_DOMAIN = 'https://ltn.gold-usergeneratedcontent.net'
    TN_DOMAIN = 'https://tn.gold-usergeneratedcontent.net'
    FRONT_DOMAIN = 'https://hitomi.la'
    REFERER = 'https://hitomi.la/'
    NOZOMI_URL = RESOURCE_DOMAIN + '/n/index-all.nozomi'
    GALLERY_JS_URL = RESOURCE_DOMAIN + '/galleries/{id}.js'
    GALLERY_JS_PREFIX_LEN = 18  # len('var galleryinfo = ')
    PAGE_SIZE = 25
    INT_SIZE = 4  # 4 bytes per big-endian int32 in nozomi index

    @classmethod
    async def fetch(cls) -> HentaiGallery:
        headers = {'Referer': cls.REFERER}
        byte_end = cls.PAGE_SIZE * cls.INT_SIZE - 1
        range_header = f'bytes=0-{byte_end}'

        res = await HttpClient.get(
            cls.NOZOMI_URL,
            headers={**headers, 'Range': range_header},
        )
        data = res.content
        id_count = len(data) // cls.INT_SIZE
        ids = [
            struct.unpack('>i', data[i * cls.INT_SIZE : (i + 1) * cls.INT_SIZE])[0]
            for i in range(id_count)
        ]

        gallery_id = random.choice(ids)  # noqa: S311
        return await cls._retrieve_gallery(gallery_id, headers)

    @classmethod
    async def _retrieve_gallery(cls, gallery_id: int, headers: dict[str, str]) -> HentaiGallery:
        url = cls.GALLERY_JS_URL.format(id=gallery_id)
        res = await HttpClient.get(url, headers=headers)
        raw = json.loads(res.text[cls.GALLERY_JS_PREFIX_LEN :])

        artists = [a['artist'] for a in raw.get('artists') or []]
        groups = [g['group'] for g in raw.get('groups') or []]
        tags = [t['tag'] for t in raw.get('tags') or []]
        lang = raw.get('language') or 'unknown'
        gallery_type = raw.get('type') or 'manga'
        date_str = raw.get('date', '')[:7]

        file_hash = raw['files'][0]['hash']
        cover_url = cls._build_thumbnail_url(file_hash)

        return HentaiGallery(
            title=raw.get('title', ''),
            japanese_title=raw.get('japanese_title'),
            artists=artists,
            groups=groups,
            tags=tags,
            gallery_type=gallery_type,
            language=lang,
            pages=len(raw.get('files') or []),
            date=date_str,
            cover_url=cover_url,
            cover_headers={'Referer': cls.REFERER},
            url=f'{cls.FRONT_DOMAIN}/galleries/{gallery_id}.html',
        )

    @classmethod
    def _build_thumbnail_url(cls, file_hash: str) -> str:
        last1 = file_hash[-1]
        last3_mid = file_hash[-3:-1]
        return f'{cls.TN_DOMAIN}/webpsmalltn/{last1}/{last3_mid}/{file_hash}.webp'


class NhentaiScraper:
    MAX_ID = 500_000
    MAX_RETRIES = 5
    NOT_FOUND = HTTPStatus.NOT_FOUND
    EXT_MAP: ClassVar[dict[str, str]] = {'j': 'jpg', 'p': 'png', 'g': 'gif', 'w': 'webp'}

    def __init__(self, mirror_url: str = 'https://nhentai.net') -> None:
        self._mirror_url = mirror_url

    async def fetch(self) -> HentaiGallery:
        for _ in range(self.MAX_RETRIES):
            gallery_id = random.randint(1, self.MAX_ID)  # noqa: S311
            try:
                res = await HttpClient.get(f'{self._mirror_url}/api/gallery/{gallery_id}')
                if res.status_code == self.NOT_FOUND:
                    continue
                res.raise_for_status()
                return self._parse(res.json())
            except Exception as exc:
                status = getattr(getattr(exc, 'response', None), 'status_code', None)
                if status == self.NOT_FOUND:
                    continue
                raise

        msg = 'Failed to fetch nhentai gallery after max retries'
        raise ExternalServiceError(msg)

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
