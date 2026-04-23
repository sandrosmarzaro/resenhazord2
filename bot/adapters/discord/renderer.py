import io
from dataclasses import dataclass
from typing import ClassVar

import aiohttp
import discord
import structlog

from bot.data.discord import BUFFER_EXTENSIONS
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.sticker_content import StickerContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage, MessageContent

logger = structlog.get_logger()


@dataclass
class DiscordReply:
    text: str | None = None
    embed: discord.Embed | None = None
    file: discord.File | None = None


class DiscordResponseRenderer:
    MAX_TEXT_LENGTH: ClassVar[int] = 2000
    MAX_EMBED_DESC_LENGTH: ClassVar[int] = 4096
    HTTP_OK: ClassVar[int] = 200
    UNSUPPORTED_MESSAGE: ClassVar[str] = 'Este tipo de conteudo nao e suportado no Discord.'
    RENDER_MAP: ClassVar[dict[type, str]] = {
        TextContent: '_render_text',
        ImageContent: '_render_image',
        ImageBufferContent: '_render_image_buffer',
        VideoContent: '_render_video',
        VideoBufferContent: '_render_video_buffer',
        AudioContent: '_render_audio',
        AudioBufferContent: '_render_audio_buffer',
        StickerContent: '_render_unsupported',
        RawContent: '_render_raw',
    }

    def render(self, message: BotMessage) -> DiscordReply:
        content = message.content
        method_name = self.RENDER_MAP.get(type(content), '_render_unsupported')
        return getattr(self, method_name)(content)

    async def render_async(self, message: BotMessage) -> DiscordReply:
        content = message.content
        logger.info('discord_render_async', content_type=type(content).__name__)
        if isinstance(content, AudioContent):
            return await self._render_audio_async(content)
        return self.render(message)

    async def render_many_async(self, messages: list[BotMessage]) -> list[DiscordReply]:
        return [await self.render_async(m) for m in messages]

    def render_many(self, messages: list[BotMessage]) -> list[DiscordReply]:
        return [self.render(m) for m in messages]

    def _render_text(self, content: TextContent) -> DiscordReply:
        embed = discord.Embed(description=content.text[: self.MAX_EMBED_DESC_LENGTH])
        return DiscordReply(embed=embed)

    def _render_image(self, content: ImageContent) -> DiscordReply:
        embed = discord.Embed()
        if content.caption:
            embed.description = content.caption
        embed.set_image(url=content.url)
        return DiscordReply(embed=embed)

    def _render_image_buffer(self, content: ImageBufferContent) -> DiscordReply:
        ext = BUFFER_EXTENSIONS.get(content.type, 'png')
        filename = f'image.{ext}'
        file = discord.File(io.BytesIO(content.data), filename=filename)
        embed = discord.Embed()
        if content.caption:
            embed.description = content.caption
        embed.set_image(url=f'attachment://{filename}')
        return DiscordReply(embed=embed, file=file)

    def _render_video(self, content: VideoContent) -> DiscordReply:
        text = content.url
        if content.caption:
            text = f'{content.caption}\n\n{content.url}'
        return DiscordReply(text=text)

    def _render_video_buffer(self, content: VideoBufferContent) -> DiscordReply:
        ext = BUFFER_EXTENSIONS.get(content.type, 'mp4')
        filename = f'video.{ext}'
        file = discord.File(io.BytesIO(content.data), filename=filename)
        return DiscordReply(text=content.caption or None, file=file)

    def _render_audio(self, content: AudioContent) -> DiscordReply:
        return DiscordReply(text=content.url)

    async def _render_audio_async(self, content: AudioContent) -> DiscordReply:
        try:
            async with aiohttp.ClientSession() as session, session.get(
                content.url, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == self.HTTP_OK:
                    data = await resp.read()
                    logger.info('discord_audio_downloaded', url=content.url, size=len(data))
                    ext = '.mp3'
                    if content.mimetype:
                        ext = BUFFER_EXTENSIONS.get(content.mimetype, '.mp3')
                    filename = f'audio{ext}'
                    file = discord.File(io.BytesIO(data), filename=filename)
                    return DiscordReply(file=file)
                logger.warning('discord_audio_http_error', url=content.url, status=resp.status)
        except aiohttp.ClientError:
            logger.warning('discord_audio_download_failed', url=content.url, exc_info=True)
        return DiscordReply(text=f'🎵 {content.url}')

    def _render_audio_buffer(self, content: AudioBufferContent) -> DiscordReply:
        ext = BUFFER_EXTENSIONS.get(content.type, 'mp4')
        filename = f'audio.{ext}'
        file = discord.File(io.BytesIO(content.data), filename=filename)
        return DiscordReply(file=file)

    def _render_raw(self, content: RawContent) -> DiscordReply:
        raw = content.content
        caption: str | None = raw.get('caption') or None
        if 'video' in raw:
            url: str = raw['video'].get('url', '')
            text = f'{caption}\n\n{url}' if caption else url
            return DiscordReply(text=text)
        if 'image' in raw:
            url = raw['image'].get('url', '')
            embed = discord.Embed()
            if caption:
                embed.description = caption
            embed.set_image(url=url)
            return DiscordReply(embed=embed)
        return DiscordReply(text=self.UNSUPPORTED_MESSAGE)

    def _render_unsupported(self, content: MessageContent) -> DiscordReply:
        logger.warning('discord_unsupported_content', content_type=type(content).__name__)
        return DiscordReply(text=self.UNSUPPORTED_MESSAGE)
