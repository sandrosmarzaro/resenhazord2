import html
import random
import re
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

    def __init__(self) -> None:
        super().__init__()
        self._redgifs = RedGifs()

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='porno',
            args=ArgType.OPTIONAL,
            args_label='categoria',
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            scope=CommandScope.NSFW,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Recebe um vídeo adulto aleatório, ou um da categoria escolhida (18+).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if parsed.rest:
            return await self._category_porn(data, parsed.rest)
        return await self._real_porn(data)

    async def _category_porn(self, data: CommandData, category: str) -> list[BotMessage]:
        tag = PORN_CATEGORIES.get(strip_accents(category.strip().lower()))
        if not tag:
            categories = ', '.join(PORN_CATEGORIES)
            return [Reply.to(data).text(f'Categoria inválida! 🫣\n\nCategorias: {categories}')]
        media = await self._redgifs.random_media(tag)
        if media.is_video:
            return [Reply.to(data).video(media.url, 'Aqui está seu vídeo 🤤')]
        return [Reply.to(data).image(media.url, 'Aqui está sua imagem 🤤')]

    async def _real_porn(self, data: CommandData) -> list[BotMessage]:
        try:
            result = await self._scrape_random_video()
            return [Reply.to(data).video(result['url'], result['title'])]
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

        video_url = next(
            (
                match.group(1)
                for pattern in cls.VIDEO_URL_PATTERNS
                if (match := re.search(pattern, page_html))
            ),
            None,
        )
        if not video_url:
            msg = 'Não foi possível extrair URL do vídeo'
            raise ExternalServiceError(msg)

        return {'url': video_url, 'title': title}
