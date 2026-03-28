from dataclasses import dataclass


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
