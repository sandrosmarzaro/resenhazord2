"""Pydantic model for the inbound command wire payload."""

from pydantic import BaseModel


class CommandPayload(BaseModel):
    text: str
    jid: str
    sender_jid: str
    participant: str | None = None
    is_group: bool = False
    expiration: int | None = None
    mentioned_jids: list[str] = []
    quoted_message_id: str | None = None
    quoted_text: str | None = None
    media_type: str | None = None
    media_source: str | None = None
    media_is_animated: bool = False
    media_caption: str | None = None
    message_id: str | None = None
    push_name: str | None = None
