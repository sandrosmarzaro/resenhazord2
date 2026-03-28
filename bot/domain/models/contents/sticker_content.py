from dataclasses import dataclass


@dataclass
class StickerContent:
    data: bytes
    pack: str = ''
    author: str = ''
    type: str = 'sticker'

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data

    def to_dict(self) -> dict:
        d: dict = {'type': self.type}
        if self.pack:
            d['pack'] = self.pack
        if self.author:
            d['author'] = self.author
        return d
