from dataclasses import dataclass


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
class AudioBufferContent:
    data: bytes
    mimetype: str = 'audio/mp4'
    type: str = 'audio_buffer'

    @property
    def has_buffer(self) -> bool:
        return True

    @property
    def buffer(self) -> bytes:
        return self.data

    def to_dict(self) -> dict:
        return {'type': self.type, 'mimetype': self.mimetype}
