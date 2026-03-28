from dataclasses import dataclass


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
    gif_playback: bool = False
    type: str = 'video_buffer'

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
        return d
