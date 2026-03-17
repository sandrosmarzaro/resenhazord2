from dataclasses import dataclass, field


@dataclass
class TextContent:
    text: str
    mentions: list[str] = field(default_factory=list)
    type: str = 'text'

    @property
    def has_buffer(self) -> bool:
        return False

    def to_dict(self) -> dict:
        d: dict = {'type': self.type, 'text': self.text}
        if self.mentions:
            d['mentions'] = self.mentions
        return d


@dataclass
class ImageContent:
    url: str
    caption: str | None = None
    view_once: bool = True
    type: str = 'image'

    @property
    def has_buffer(self) -> bool:
        return False

    def to_dict(self) -> dict:
        d: dict = {'type': self.type, 'url': self.url, 'view_once': self.view_once}
        if self.caption:
            d['caption'] = self.caption
        return d


@dataclass
class ImageBufferContent:
    data: bytes
    caption: str | None = None
    view_once: bool = True
    type: str = 'image_buffer'

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data

    def to_dict(self) -> dict:
        d: dict = {'type': self.type, 'view_once': self.view_once}
        if self.caption:
            d['caption'] = self.caption
        return d


@dataclass
class VideoContent:
    url: str
    caption: str | None = None
    view_once: bool = True
    type: str = 'video'

    @property
    def has_buffer(self) -> bool:
        return False

    def to_dict(self) -> dict:
        d: dict = {'type': self.type, 'url': self.url, 'view_once': self.view_once}
        if self.caption:
            d['caption'] = self.caption
        return d


@dataclass
class VideoBufferContent:
    data: bytes
    caption: str | None = None
    view_once: bool = True
    type: str = 'video_buffer'

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data

    def to_dict(self) -> dict:
        d: dict = {'type': self.type, 'view_once': self.view_once}
        if self.caption:
            d['caption'] = self.caption
        return d


@dataclass
class AudioContent:
    url: str
    view_once: bool = True
    mimetype: str = 'audio/mp4'
    type: str = 'audio'

    @property
    def has_buffer(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'url': self.url,
            'view_once': self.view_once,
            'mimetype': self.mimetype,
        }


@dataclass
class StickerContent:
    data: bytes
    type: str = 'sticker'

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data

    def to_dict(self) -> dict:
        return {'type': self.type}


@dataclass
class RawContent:
    content: dict
    type: str = 'raw'

    @property
    def has_buffer(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {'type': self.type, 'content': self.content}


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
            'jid': self.jid,
            'content': self.content.to_dict(),
        }
        if self.quoted_message_id:
            result['quoted_message_id'] = self.quoted_message_id
        if self.expiration:
            result['expiration'] = self.expiration
        return result
