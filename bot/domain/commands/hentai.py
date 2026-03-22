import json
import random
import struct
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from typing import ClassVar

import httpx
import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


@dataclass(frozen=True)
class HentaiGallery:
    title: str
    japanese_title: str | None
    artists: list[str]
    groups: list[str]
    tags: list[str]
    gallery_type: str
    language: str
    pages: int
    date: str
    cover_url: str
    cover_headers: dict[str, str] = field(default_factory=dict)
    url: str = ''


class HitomiScraper:
    """Scrapes Hitomi.la via its nozomi index and gallery JS API."""

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
    """Fetches random galleries from nhentai API."""

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
        raise ValueError(msg)

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


class HentaiCommand(Command):
    MAX_TAGS_SHOWN = 10
    COVER_RETRIES = 3

    def __init__(self, nhentai_mirror_url: str = 'https://nhentai.net') -> None:
        super().__init__()
        self._nhentai = NhentaiScraper(mirror_url=nhentai_mirror_url)

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='hentai',
            flags=['dm', 'show', 'hitomi', 'nhentai'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Envia um hentai aleatório com informações do Hitomi.la.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        fetch_fn = self._select_source(parsed)

        last_error: Exception | None = None
        for _ in range(self.COVER_RETRIES):
            try:
                gallery = await fetch_fn()
                cover = await HttpClient.get_buffer(
                    gallery.cover_url,
                    headers=gallery.cover_headers,
                )
                caption = self._build_caption(gallery)
                return [Reply.to(data).image_buffer(cover, caption)]
            except Exception as exc:
                last_error = exc
                logger.exception('hentai_fetch_error')

        if last_error:
            raise last_error
        msg = 'All hentai fetch attempts failed'
        raise RuntimeError(msg)

    def _select_source(self, parsed: ParsedCommand):
        if 'hitomi' in parsed.flags:
            return HitomiScraper.fetch
        if 'nhentai' in parsed.flags:
            return self._nhentai.fetch
        return self._fetch_default

    async def _fetch_default(self) -> HentaiGallery:
        try:
            return await HitomiScraper.fetch()
        except (httpx.HTTPError, ValueError, KeyError, IndexError):
            return await self._nhentai.fetch()

    @classmethod
    def _build_caption(cls, g: HentaiGallery) -> str:
        has_jap = g.japanese_title and g.japanese_title != g.title
        jap_title = f'\n🗾 _{g.japanese_title}_' if has_jap else ''
        artists = ', '.join(g.artists) if g.artists else '—'
        groups = ', '.join(g.groups) if g.groups else '—'

        shown_tags = g.tags[: cls.MAX_TAGS_SHOWN]
        extra = len(g.tags) - cls.MAX_TAGS_SHOWN
        extra_suffix = f' (+{extra} more)' if extra > 0 else ''
        tags_str = ', '.join(shown_tags) + extra_suffix if shown_tags else '—'

        return '\n'.join(
            [
                f'📖 *{g.title}*{jap_title}',
                '',
                f'✍️ {artists}',
                f'👥 {groups}',
                f'📚 {g.gallery_type}',
                f'🌐 {g.language}',
                '',
                f'🏷️ {tags_str}',
                f'📄 {g.pages}',
                f'📅 {g.date}',
                '',
                f'🔗 {g.url}',
            ]
        )
