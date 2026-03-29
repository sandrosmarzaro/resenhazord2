import json
import random
import struct

import httpx

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
        page_bytes = cls.PAGE_SIZE * cls.INT_SIZE - 1

        res = await HttpClient.get(
            cls.NOZOMI_URL,
            headers={**headers, 'Range': f'bytes=0-{page_bytes}'},
        )

        total_ids = cls._parse_total_ids(res)
        data = res.content

        if total_ids > cls.PAGE_SIZE:
            page_start = random.randint(0, total_ids - cls.PAGE_SIZE)  # noqa: S311
            byte_start = page_start * cls.INT_SIZE
            res = await HttpClient.get(
                cls.NOZOMI_URL,
                headers={**headers, 'Range': f'bytes={byte_start}-{byte_start + page_bytes}'},
            )
            data = res.content

        id_count = len(data) // cls.INT_SIZE
        ids = [
            struct.unpack('>i', data[i * cls.INT_SIZE : (i + 1) * cls.INT_SIZE])[0]
            for i in range(id_count)
        ]

        if not ids:
            msg = 'Hitomi returned empty gallery index'
            raise ExternalServiceError(msg)

        gallery_id = random.choice(ids)  # noqa: S311
        return await cls._retrieve_gallery(gallery_id, headers)

    @classmethod
    def _parse_total_ids(cls, res: httpx.Response) -> int:
        content_range = res.headers.get('content-range', '')
        if '/' in content_range:
            total_str = content_range.split('/')[-1]
            if total_str.isdigit():
                return int(total_str) // cls.INT_SIZE
        return cls.PAGE_SIZE

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
