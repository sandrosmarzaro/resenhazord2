"""Pydantic models for WebSocket message types."""

from typing import Any

from pydantic import BaseModel


class WSCommandData(BaseModel):
    text: str
    jid: str
    sender_jid: str
    participant: str | None = None
    is_group: bool = False
    expiration: int | None = None
    mentioned_jids: list[str] = []
    quoted_message_id: str | None = None
    has_media: bool = False
    media_type: str | None = None
    message_id: str | None = None
    push_name: str | None = None


class WSMessage(BaseModel):
    id: str
    type: str
    method: str | None = None
    data: dict[str, Any] | None = None
