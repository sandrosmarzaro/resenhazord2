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
