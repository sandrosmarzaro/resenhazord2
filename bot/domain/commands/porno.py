import html
import random
import re

import structlog
from bs4 import BeautifulSoup

from bot.data.browser_headers import BROWSER_HEADERS
from bot.data.nsfw_tags import NSFW_TAGS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class PornoCommand(Command):
    MAX_PAGE = 50

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='porno',
            flags=['ia', Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um porno aleatório real ou feito por IA.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'ia' in parsed.flags:
            return await self._ia_porn(data, parsed)
        return await self._real_porn(data)

    async def _ia_porn(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        tag = random.choice(NSFW_TAGS)  # noqa: S311
        response = await HttpClient.get(
            f'https://nsfwhub.onrender.com/nsfw?type={tag}',
            timeout=30.0,
        )
        response.raise_for_status()
        porn = response.json()
        url: str = porn['image']['url']

        view_once = 'show' not in parsed.flags
        caption_map = {'.mp4': 'vídeo', '.gif': 'GIF'}
        ext = url[url.rfind('.') :] if '.' in url.rsplit('/', 1)[-1] else ''
        media_label = caption_map.get(ext, 'imagem')
        content: dict = {'viewOnce': view_once, 'caption': f'Aqui está seu {media_label} 🤤'}

        if ext == '.mp4':
            content['video'] = {'url': url}
        elif ext == '.gif':
            content['image'] = {'url': url}
            content['gifPlayback'] = True
        else:
            content['image'] = {'url': url}

        return [Reply.to(data).raw(content)]

    async def _real_porn(self, data: CommandData) -> list[BotMessage]:
        try:
            result = await self._scrape_random_video()
            return [Reply.to(data).video(result['url'], result['title'])]
        except Exception:
            logger.exception('porno_scrape_failed')
            return [
                Reply.to(data).text(
                    'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶'
                )
            ]

    @classmethod
    async def _scrape_random_video(cls) -> dict[str, str]:
        page = random.randint(1, cls.MAX_PAGE)  # noqa: S311
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

        random_link = random.choice(links)  # noqa: S311
        video_page_url = f'https://www.xvideos.com{random_link}'

        video_resp = await HttpClient.get(video_page_url, timeout=30.0, headers=BROWSER_HEADERS)
        video_resp.raise_for_status()
        page_html = video_resp.text

        title_match = re.search(r'<title>([^<]+)</title>', page_html)
        if title_match:
            title = html.unescape(title_match.group(1).replace(' - XVIDEOS.COM', '').strip())
        else:
            title = 'Vídeo'

        low_match = re.search(r"setVideoUrlLow\('([^']+)'\)", page_html)
        high_match = re.search(r"setVideoUrlHigh\('([^']+)'\)", page_html)
        video_url = (
            low_match.group(1) if low_match else (high_match.group(1) if high_match else None)
        )

        if not video_url:
            msg = 'Não foi possível extrair URL do vídeo'
            raise ExternalServiceError(msg)

        return {'url': video_url, 'title': title}
