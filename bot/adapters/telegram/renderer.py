from dataclasses import replace
from typing import ClassVar

import structlog

from bot.adapters.telegram.formatter import whatsapp_to_html
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.sticker_content import StickerContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage, MessageContent
from bot.ports.telegram_port import TelegramKind, TelegramOutbound

logger = structlog.get_logger()

_VOICE_AUDIO_TYPE = 'audio_ogg'


class TelegramResponseRenderer:
    MAX_TEXT_LENGTH: ClassVar[int] = 4096
    MAX_CAPTION_LENGTH: ClassVar[int] = 1024
    UNSUPPORTED_MESSAGE: ClassVar[str] = 'Este tipo de conteudo ainda nao e suportado no Telegram.'
    RENDER_MAP: ClassVar[dict[type, str]] = {
        TextContent: '_render_text',
        ImageContent: '_render_image',
        ImageBufferContent: '_render_image_buffer',
        VideoContent: '_render_video',
        VideoBufferContent: '_render_video_buffer',
        AudioContent: '_render_audio',
        AudioBufferContent: '_render_audio_buffer',
        StickerContent: '_render_sticker',
        RawContent: '_render_raw',
    }

    def render(self, message: BotMessage, chat_id: int) -> list[TelegramOutbound]:
        content = message.content
        method_name = self.RENDER_MAP.get(type(content), '_render_unsupported')
        return getattr(self, method_name)(content, chat_id)

    def render_many(self, messages: list[BotMessage], chat_id: int) -> list[TelegramOutbound]:
        outbounds: list[TelegramOutbound] = []
        for message in messages:
            outbounds.extend(self.render(message, chat_id))
        return outbounds

    def _render_text(self, content: TextContent, chat_id: int) -> list[TelegramOutbound]:
        return [
            TelegramOutbound(kind=TelegramKind.TEXT, chat_id=chat_id, text=whatsapp_to_html(chunk))
            for chunk in self._split(content.text, self.MAX_TEXT_LENGTH)
        ]

    def _render_image(self, content: ImageContent, chat_id: int) -> list[TelegramOutbound]:
        media = TelegramOutbound(kind=TelegramKind.PHOTO, chat_id=chat_id, url=content.url)
        return self._with_caption(media, content.caption)

    def _render_image_buffer(
        self, content: ImageBufferContent, chat_id: int
    ) -> list[TelegramOutbound]:
        media = TelegramOutbound(
            kind=TelegramKind.PHOTO, chat_id=chat_id, buffer=content.data, filename='image.png'
        )
        return self._with_caption(media, content.caption)

    def _render_video(self, content: VideoContent, chat_id: int) -> list[TelegramOutbound]:
        media = TelegramOutbound(kind=TelegramKind.VIDEO, chat_id=chat_id, url=content.url)
        return self._with_caption(media, content.caption)

    def _render_video_buffer(
        self, content: VideoBufferContent, chat_id: int
    ) -> list[TelegramOutbound]:
        kind = TelegramKind.ANIMATION if content.gif_playback else TelegramKind.VIDEO
        media = TelegramOutbound(
            kind=kind, chat_id=chat_id, buffer=content.data, filename='video.mp4'
        )
        return self._with_caption(media, content.caption)

    def _render_audio(self, content: AudioContent, chat_id: int) -> list[TelegramOutbound]:
        return [TelegramOutbound(kind=TelegramKind.AUDIO, chat_id=chat_id, url=content.url)]

    def _render_audio_buffer(
        self, content: AudioBufferContent, chat_id: int
    ) -> list[TelegramOutbound]:
        kind = TelegramKind.VOICE if content.type == _VOICE_AUDIO_TYPE else TelegramKind.AUDIO
        filename = 'audio.ogg' if kind == TelegramKind.VOICE else 'audio.mp3'
        return [
            TelegramOutbound(kind=kind, chat_id=chat_id, buffer=content.data, filename=filename)
        ]

    def _render_sticker(self, content: StickerContent, chat_id: int) -> list[TelegramOutbound]:
        return [
            TelegramOutbound(
                kind=TelegramKind.STICKER,
                chat_id=chat_id,
                buffer=content.data,
                filename='sticker.webp',
            )
        ]

    def _render_raw(self, content: RawContent, chat_id: int) -> list[TelegramOutbound]:
        raw = content.content
        caption: str | None = raw.get('caption') or None
        gif_playback = bool(raw.get('gifPlayback'))
        if 'video' in raw:
            kind = TelegramKind.ANIMATION if gif_playback else TelegramKind.VIDEO
            url = raw['video'].get('url', '')
            media = TelegramOutbound(kind=kind, chat_id=chat_id, url=url)
            return self._with_caption(media, caption)
        if 'image' in raw:
            kind = TelegramKind.ANIMATION if gif_playback else TelegramKind.PHOTO
            url = raw['image'].get('url', '')
            media = TelegramOutbound(kind=kind, chat_id=chat_id, url=url)
            return self._with_caption(media, caption)
        return self._render_unsupported(content, chat_id)

    def _render_unsupported(self, content: MessageContent, chat_id: int) -> list[TelegramOutbound]:
        logger.warning('telegram_unsupported_content', content_type=type(content).__name__)
        return [
            TelegramOutbound(kind=TelegramKind.TEXT, chat_id=chat_id, text=self.UNSUPPORTED_MESSAGE)
        ]

    @classmethod
    def _with_caption(cls, media: TelegramOutbound, caption: str | None) -> list[TelegramOutbound]:
        if not caption:
            return [media]
        if len(caption) <= cls.MAX_CAPTION_LENGTH:
            return [replace(media, text=whatsapp_to_html(caption))]
        overflow = TelegramOutbound(
            kind=TelegramKind.TEXT, chat_id=media.chat_id, text=whatsapp_to_html(caption)
        )
        return [media, overflow]

    @staticmethod
    def _split(text: str, limit: int) -> list[str]:
        if len(text) <= limit:
            return [text]
        return [text[i : i + limit] for i in range(0, len(text), limit)]
