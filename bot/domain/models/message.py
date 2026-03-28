"""Re-exports all message content types from their individual modules."""

from dataclasses import dataclass

from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.sticker_content import StickerContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent

__all__ = [
    'AudioBufferContent',
    'AudioContent',
    'BotMessage',
    'ImageBufferContent',
    'ImageContent',
    'MessageContent',
    'RawContent',
    'StickerContent',
    'TextContent',
    'VideoBufferContent',
    'VideoContent',
]

MessageContent = (
    TextContent
    | ImageContent
    | ImageBufferContent
    | VideoContent
    | VideoBufferContent
    | AudioContent
    | AudioBufferContent
    | StickerContent
    | RawContent
)


@dataclass
class BotMessage:
    jid: str
    content: MessageContent
    quoted_message_id: str | None = None
    expiration: int | None = None

    def to_dict(self) -> dict:
        result: dict = {
            'jid': self.jid,
            'content': self.content.to_dict(),
        }
        if self.quoted_message_id:
            result['quoted_message_id'] = self.quoted_message_id
        if self.expiration:
            result['expiration'] = self.expiration
        return result
