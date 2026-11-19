import base64
from dataclasses import dataclass


@dataclass
class VideoContent:
    url: str
    caption: str | None = None
    view_once: bool = True
    type: str = 'video'
    jpeg_thumbnail: bytes | None = None

    @property
    def has_buffer(self) -> bool:
        return False

    def to_dict(self) -> dict:
        d: dict = {'type': self.type, 'url': self.url, 'view_once': self.view_once}
        if self.caption:
            d['caption'] = self.caption
        if self.jpeg_thumbnail:
            d['jpeg_thumbnail'] = base64.b64encode(self.jpeg_thumbnail).decode()
        return d


@dataclass
class VideoBufferContent:
    data: bytes
    caption: str | None = None
    view_once: bool = True
    gif_playback: bool = False
    mentions: list[str] | None = None
    type: str = 'video_buffer'
    jpeg_thumbnail: bytes | None = None

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data

    def to_dict(self) -> dict:
        d: dict = {'type': self.type, 'view_once': self.view_once}
        if self.gif_playback:
            d['gif_playback'] = True
        if self.caption:
            d['caption'] = self.caption
        if self.mentions:
            d['mentions'] = self.mentions
        if self.jpeg_thumbnail:
            d['jpeg_thumbnail'] = base64.b64encode(self.jpeg_thumbnail).decode()
        return d
