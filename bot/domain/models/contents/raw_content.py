from dataclasses import dataclass


@dataclass
class RawContent:
    content: dict
    type: str = 'raw'

    @property
    def has_buffer(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {'type': self.type, 'content': self.content}
