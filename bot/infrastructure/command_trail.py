import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, ClassVar

import sentry_sdk

from bot.domain.models.command_data import CommandData
from bot.infrastructure.execution_store import ExecutionStore
from bot.infrastructure.runtime_metrics import HostGauges
from bot.infrastructure.telemetry_buffer import TelemetryBuffer
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class CommandTrail:
    """What one command left behind in this process, kept until its reply is out.

    The platform opens a trail around a command and its reply. While it is open the
    capture processors copy the spans and logs the command emits into it, Command.run
    notes how the run went, and the platform names each reply it sent. On close it
    becomes one execution record, stored under those replies, and its buffers are
    released.
    """

    _CURRENT: ClassVar[ContextVar['CommandTrail | None']] = ContextVar(
        'command_trail', default=None
    )

    def __init__(self, data: CommandData, origin: dict[str, Any]) -> None:
        self.spans = TelemetryBuffer()
        self.logs = TelemetryBuffer()
        self.execution: dict[str, Any] | None = None
        self._data = data
        self._origin = origin
        self._replies: dict[str, str] = {}

    @classmethod
    def current(cls) -> CommandTrail | None:
        return cls._CURRENT.get()

    @classmethod
    @asynccontextmanager
    async def open(
        cls, data: CommandData, *, correlation_id: str | None = None, attempt: int = 1
    ) -> AsyncIterator[CommandTrail]:
        correlation_id = correlation_id or uuid.uuid4().hex
        trail = cls(data, cls._describe(data, correlation_id, attempt))
        token = cls._CURRENT.set(trail)
        try:
            # Every Sentry event of the command carries the id the record shows. Each
            # command gets its own scope, so concurrent ones keep their own tag.
            with sentry_sdk.isolation_scope():
                sentry_sdk.set_tag('correlation_id', correlation_id)
                yield trail
        finally:
            cls._CURRENT.reset(token)
            await trail._close()

    def remember(self, message_id: str | None, summary: str) -> None:
        if message_id:
            self._replies[message_id] = TelemetryRedactor.value(summary)

    async def _close(self) -> None:
        spans, spans_dropped = self.spans.drain()
        logs, logs_dropped = self.logs.drain()
        record = {
            **self._origin,
            'execution': self.execution,
            'spans': spans,
            'spans_dropped': spans_dropped,
            'logs': logs,
            'logs_dropped': logs_dropped,
            'host': HostGauges.snapshot(),
            'replies': self._replies,
        }
        await ExecutionStore.instance().save(
            record, str(self._data.platform), self._data.jid, list(self._replies)
        )

    @staticmethod
    def _describe(data: CommandData, correlation_id: str, attempt: int) -> dict[str, Any]:
        return {
            'platform': data.platform,
            'chat_type': 'group' if data.is_group else 'private',
            'chat': TelemetryRedactor.identity(data.jid),
            'sender': TelemetryRedactor.identity(data.sender_jid),
            'message_id': data.message_id,
            'correlation_id': correlation_id,
            'attempt': attempt,
            'received_at': datetime.now(UTC).isoformat(),
        }
