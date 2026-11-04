from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from bot.ports.command_inbox_port import CommandInboxPort


class DeliveryGuard:
    def __init__(self, inbox: CommandInboxPort | None) -> None:
        self._inbox = inbox
        self._running: set[str] = set()

    @contextmanager
    def claim(self, envelope: dict[str, Any]) -> Iterator[bool]:
        # The inbox only knows finished commands, so a duplicate arriving mid-run gets past
        # it (and ,dl stays mid-run for its whole wait in the lane). This has to die with
        # the process: a durable claim would outlive a crash and block the redelivery that
        # ADR 0001 counts on. No await between the check and the add, so asyncio can't
        # interleave them; it holds while a single process consumes. A replay is the
        # operator asking for one more run, so it neither checks nor takes the claim.
        key = None if envelope.get('replayed') else self._key(envelope)
        if key in self._running:
            yield False
            return
        if key:
            self._running.add(key)
        try:
            yield True
        finally:
            if key:
                self._running.discard(key)

    async def already_answered(self, envelope: dict[str, Any]) -> bool:
        key = self._key(envelope)
        # A dead letter already got its error reply; a replay asks to run it again.
        if self._inbox is None or key is None or envelope.get('replayed'):
            return False
        return await self._inbox.is_done(key)

    async def mark_answered(self, envelope: dict[str, Any]) -> None:
        key = self._key(envelope)
        if self._inbox is None or key is None:
            return
        await self._inbox.mark_done(key)

    @staticmethod
    def _key(envelope: dict[str, Any]) -> str | None:
        # WhatsApp message ids are only unique within a chat.
        data = envelope['data']
        message_id = data.get('message_id')
        return f'{data["jid"]}:{message_id}' if message_id else None
