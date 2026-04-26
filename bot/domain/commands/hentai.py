import httpx
import structlog

from bot.data.hentai_gallery import HentaiGallery
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.exceptions import BotError, ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.hentai.hitomi_scraper import HitomiScraper
from bot.domain.services.hentai.nhentai_scraper import NhentaiScraper
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class HentaiCommand(Command):
    MAX_TAGS_SHOWN = 10
    COVER_RETRIES = 3

    def __init__(self, nhentai_mirror_url: str = 'https://nhentai.to') -> None:
        super().__init__()
        self._nhentai = NhentaiScraper(mirror_url=nhentai_mirror_url)

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='hentai',
            flags=[Flag.DM, Flag.SHOW, 'hitomi', 'nhentai'],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
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
            except BotError:
                raise
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
        except (httpx.HTTPError, ValueError, KeyError, IndexError, ExternalServiceError):
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
