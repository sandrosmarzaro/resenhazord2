import html
import random
import re
import unicodedata
from typing import ClassVar

import structlog
lazy from bs4 import BeautifulSoup  # type: ignore[syntax]

from bot.data.browser_headers import BROWSER_HEADERS
from bot.data.porn_categories import PORN_CATEGORIES
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Category,
    Command,
    CommandConfig,
    CommandScope,
    Flag,
    ParsedCommand,
    Platform,
)
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.minors_filter import MinorsFilter
from bot.domain.services.redgifs import RedGifs
from bot.domain.text import strip_accents
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class PornoCommand(Command):
    MAX_PAGE = 50
    # Where a law requires age verification (Arizona, Wyoming), xvideos leaves the player
    # calls out of the page but keeps the mp4 in its JSON-LD contentUrl.
    VIDEO_URL_PATTERNS: ClassVar[tuple[str, ...]] = (
        r"setVideoUrlLow\('([^']+)'\)",
        r"setVideoUrlHigh\('([^']+)'\)",
        r'"contentUrl"\s*:\s*"([^"]+)"',
    )
    # WhatsApp's thumbnail is drawn from the page's preview image, not the whole video.
    THUMBNAIL_URL_PATTERNS: ClassVar[tuple[str, ...]] = (
        r'<meta property="og:image" content="([^"]+)"',
        r'"thumbnailUrl"\s*:\s*\[?\s*"([^"]+)"',
    )

    # The minors check and the search see the same plain string: anything outside it
    # (invisible characters, lookalike letters, punctuation) splits the word instead.
    NOT_SEARCHABLE: ClassVar[re.Pattern[str]] = re.compile(r'[^a-z0-9]+')
    INVISIBLE_CATEGORY = 'Cf'

    def __init__(self) -> None:
        super().__init__()
        self._redgifs = RedGifs()

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='porno',
            aliases=['porn'],
            args=ArgType.OPTIONAL,
            args_label='busca',
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            scope=CommandScope.NSFW,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Recebe um vídeo adulto aleatório, ou um da sua busca (18+).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if term := self._search_term(parsed.rest):
            return await self._searched_porn(data, term)
        return await self._real_porn(data)

    @classmethod
    def _search_term(cls, text: str) -> str:
        visible = ''.join(
            char
            for char in unicodedata.normalize('NFKC', text)
            if unicodedata.category(char) != cls.INVISIBLE_CATEGORY
        )
        return cls.NOT_SEARCHABLE.sub(' ', strip_accents(visible.casefold())).strip()

    async def _searched_porn(self, data: CommandData, term: str) -> list[BotMessage]:
        if MinorsFilter.flags('redgifs', [term]):
            return [Reply.to(data).text('Essa busca não rola 🚫')]
        media = await self._redgifs.random_media(PORN_CATEGORIES.get(term, term))
        if media.is_video:
            video = await RedGifs.download(media.url)
            return [Reply.to(data).video_buffer(video, 'Aqui está seu vídeo 🤤')]
        return [Reply.to(data).image(media.url, 'Aqui está sua imagem 🤤')]

    async def _real_porn(self, data: CommandData) -> list[BotMessage]:
        try:
            result = await self._scrape_random_video()
            thumbnail_url = result.get('thumbnail_url')
            return [
                Reply.to(data).video(result['url'], result['title'], thumbnail_url=thumbnail_url)
            ]
        except Exception:
            logger.exception('upstream_failed', upstream='xvideos')
            return [
                Reply.to(data).text(
                    'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶'
                )
            ]

    @classmethod
    async def _scrape_random_video(cls) -> dict[str, str]:
        page = random.randint(1, cls.MAX_PAGE)
        listing_url = f'https://www.xvideos.com/new/{page}'

        listing_resp = await HttpClient.get(listing_url, timeout=30.0, headers=BROWSER_HEADERS)
        listing_resp.raise_for_status()

        soup = BeautifulSoup(listing_resp.text, 'html.parser')
        links: list[str] = []
        for a in soup.select('div.thumb-block a[href^="/video"]'):
            href = a.get('href')
            if isinstance(href, str) and href not in links:
                links.append(href)

        if not links:
            msg = 'Nenhum vídeo encontrado na listagem'
            raise ExternalServiceError(msg)

        random_link = random.choice(links)
        video_page_url = f'https://www.xvideos.com{random_link}'

        video_resp = await HttpClient.get(video_page_url, timeout=30.0, headers=BROWSER_HEADERS)
        video_resp.raise_for_status()
        page_html = video_resp.text

        title_match = re.search(r'<title>([^<]+)</title>', page_html)
        if title_match:
            title = html.unescape(title_match.group(1).replace(' - XVIDEOS.COM', '').strip())
        else:
            title = 'Vídeo'

        video_url = cls._first_match(cls.VIDEO_URL_PATTERNS, page_html)
        if not video_url:
            msg = 'Não foi possível extrair URL do vídeo'
            raise ExternalServiceError(msg)

        video = {'url': video_url, 'title': title}
        thumbnail_url = cls._first_match(cls.THUMBNAIL_URL_PATTERNS, page_html)
        if thumbnail_url:
            video['thumbnail_url'] = thumbnail_url
        return video

    @staticmethod
    def _first_match(patterns: tuple[str, ...], page_html: str) -> str | None:
        return next(
            (match.group(1) for pattern in patterns if (match := re.search(pattern, page_html))),
            None,
        )
