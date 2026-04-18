from typing import ClassVar

import structlog

from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.sticker_content import StickerContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage, MessageContent
from bot.ports.telegram_port import TelegramKind, TelegramOutbound

logger = structlog.get_logger()


class TelegramResponseRenderer:
    MAX_TEXT_LENGTH: ClassVar[int] = 4096
    MAX_CAPTION_LENGTH: ClassVar[int] = 1024
    UNSUPPORTED_MESSAGE: ClassVar[str] = 'Este tipo de conteudo ainda nao e suportado no Telegram.'
    RENDER_MAP: ClassVar[dict[type, str]] = {
        TextContent: '_render_text',
        ImageContent: '_render_unsupported',
        ImageBufferContent: '_render_unsupported',
        VideoContent: '_render_unsupported',
        VideoBufferContent: '_render_unsupported',
        AudioContent: '_render_unsupported',
        AudioBufferContent: '_render_unsupported',
        StickerContent: '_render_unsupported',
        RawContent: '_render_unsupported',
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
            TelegramOutbound(kind=TelegramKind.TEXT, chat_id=chat_id, text=chunk)
            for chunk in self._split(content.text, self.MAX_TEXT_LENGTH)
        ]

    def _render_unsupported(self, content: MessageContent, chat_id: int) -> list[TelegramOutbound]:
        logger.warning('telegram_unsupported_content', content_type=type(content).__name__)
        return [
            TelegramOutbound(kind=TelegramKind.TEXT, chat_id=chat_id, text=self.UNSUPPORTED_MESSAGE)
        ]

    @staticmethod
    def _split(text: str, limit: int) -> list[str]:
        if len(text) <= limit:
            return [text]
        return [text[i : i + limit] for i in range(0, len(text), limit)]
