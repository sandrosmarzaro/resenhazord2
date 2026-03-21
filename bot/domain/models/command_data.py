from dataclasses import dataclass, field
from typing import Self


@dataclass(frozen=True)
class CommandData:
    """Platform-agnostic command data received from the TS bridge."""

    text: str
    jid: str
    sender_jid: str
    participant: str | None = None
    is_group: bool = False
    expiration: int | None = None
    mentioned_jids: list[str] = field(default_factory=list)
    quoted_message_id: str | None = None
    quoted_text: str | None = None
    media_type: str | None = None
    media_source: str | None = None
    media_is_animated: bool = False
    media_caption: str | None = None
    media_buffer: bytes | None = None
    message_id: str | None = None
    push_name: str | None = None

    @property
    def has_media(self) -> bool:
        return self.media_type is not None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            text=data['text'],
            jid=data['jid'],
            sender_jid=data['sender_jid'],
            participant=data.get('participant'),
            is_group=data.get('is_group', False),
            expiration=data.get('expiration'),
            mentioned_jids=data.get('mentioned_jids', []),
            quoted_message_id=data.get('quoted_message_id'),
            quoted_text=data.get('quoted_text'),
            media_type=data.get('media_type'),
            media_source=data.get('media_source'),
            media_is_animated=data.get('media_is_animated', False),
            media_caption=data.get('media_caption'),
            media_buffer=data.get('media_buffer'),
            message_id=data.get('message_id'),
            push_name=data.get('push_name'),
        )
