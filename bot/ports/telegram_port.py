from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class TelegramKind(StrEnum):
    TEXT = 'text'
    PHOTO = 'photo'
    VIDEO = 'video'
    AUDIO = 'audio'
    VOICE = 'voice'
    DOCUMENT = 'document'
    STICKER = 'sticker'
    ANIMATION = 'animation'


@dataclass(frozen=True)
class TelegramOutbound:
    kind: TelegramKind
    chat_id: int
    text: str | None = None
    buffer: bytes | None = None
    url: str | None = None
    filename: str | None = None


class TelegramPort(Protocol):
    async def send(self, outbound: TelegramOutbound) -> None: ...

    async def send_typing(self, chat_id: int) -> None: ...

    async def react(self, chat_id: int, message_id: int, emoji: str) -> None: ...
