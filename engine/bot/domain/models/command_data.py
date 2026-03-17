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
    has_media: bool = False
    media_type: str | None = None
    message_id: str | None = None
    push_name: str | None = None

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
            has_media=data.get('has_media', False),
            media_type=data.get('media_type'),
            message_id=data.get('message_id'),
            push_name=data.get('push_name'),
        )
