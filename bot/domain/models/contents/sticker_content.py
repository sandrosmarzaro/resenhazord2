import base64
from dataclasses import dataclass


@dataclass
class StickerContent:
    data: bytes
    pack: str = ''
    author: str = ''
    # WhatsApp audio stickers: ogg/opus played over the animation. Other platforms
    # drop it.
    audio: bytes | None = None
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
        if self.audio:
            d['audio_b64'] = base64.b64encode(self.audio).decode()
        return d
