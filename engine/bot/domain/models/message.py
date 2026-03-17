from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TextContent:
    text: str
    mentions: list[str] = field(default_factory=list)
    type: str = "text"

    @property
    def has_buffer(self) -> bool:
        return False


@dataclass
class ImageContent:
    url: str
    caption: str | None = None
    view_once: bool = True
    type: str = "image"

    @property
    def has_buffer(self) -> bool:
        return False


@dataclass
class ImageBufferContent:
    data: bytes
    caption: str | None = None
    view_once: bool = True
    type: str = "image_buffer"

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data


@dataclass
class VideoContent:
    url: str
    caption: str | None = None
    view_once: bool = True
    type: str = "video"

    @property
    def has_buffer(self) -> bool:
        return False


@dataclass
class VideoBufferContent:
    data: bytes
    caption: str | None = None
    view_once: bool = True
    type: str = "video_buffer"

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data


@dataclass
class AudioContent:
    url: str
    view_once: bool = True
    mimetype: str = "audio/mp4"
    type: str = "audio"

    @property
    def has_buffer(self) -> bool:
        return False


@dataclass
class StickerContent:
    data: bytes
    type: str = "sticker"

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data


@dataclass
class RawContent:
    content: dict
    type: str = "raw"

    @property
    def has_buffer(self) -> bool:
        return False


MessageContent = (
    TextContent
    | ImageContent
    | ImageBufferContent
    | VideoContent
    | VideoBufferContent
    | AudioContent
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
            "jid": self.jid,
            "content": self._content_to_dict(),
        }
        if self.quoted_message_id:
            result["quoted_message_id"] = self.quoted_message_id
        if self.expiration:
            result["expiration"] = self.expiration
        return result

    def _content_to_dict(self) -> dict:
        content = self.content
        d: dict = {"type": content.type}
        if isinstance(content, TextContent):
            d["text"] = content.text
            if content.mentions:
                d["mentions"] = content.mentions
        elif isinstance(content, ImageContent):
            d["url"] = content.url
            if content.caption:
                d["caption"] = content.caption
            d["view_once"] = content.view_once
        elif isinstance(content, ImageBufferContent):
            if content.caption:
                d["caption"] = content.caption
            d["view_once"] = content.view_once
        elif isinstance(content, VideoContent):
            d["url"] = content.url
            if content.caption:
                d["caption"] = content.caption
            d["view_once"] = content.view_once
        elif isinstance(content, VideoBufferContent):
            if content.caption:
                d["caption"] = content.caption
            d["view_once"] = content.view_once
        elif isinstance(content, AudioContent):
            d["url"] = content.url
            d["view_once"] = content.view_once
            d["mimetype"] = content.mimetype
        elif isinstance(content, StickerContent):
            pass  # buffer sent as binary frame
        elif isinstance(content, RawContent):
            d["content"] = content.content
        return d
