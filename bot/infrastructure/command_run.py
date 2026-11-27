import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from opentelemetry.trace import Span, format_trace_id

from bot.infrastructure.command_trail import CommandTrail
from bot.infrastructure.failure_snapshot import FailureSnapshot
from bot.infrastructure.telemetry_redactor import TelemetryRedactor

if TYPE_CHECKING:
    from bot.domain.parsers.command_parser import CommandParser


class CommandRun:
    """How one Command.run went, noted on the open trail for a bug report."""

    _MS_PER_SECOND: ClassVar[int] = 1000

    def __init__(self, name: str, text: str) -> None:
        self._name = name
        self._text = text
        self._started_at = datetime.now(UTC)
        self._started = time.monotonic()

    def end(
        self, span: Span, outcome: str, failure: BaseException | None, parser: CommandParser
    ) -> None:
        trail = CommandTrail.current()
        if trail is None:
            return
        parsed = parser.parse(self._text)
        context = span.get_span_context()
        # The user's own text, redacted, is the one free text a report keeps on purpose:
        # a dev chose to file it, and it is what reproduces the bug.
        trail.execution = {
            'command': self._name,
            'text': TelemetryRedactor.value(self._text),
            'flags': sorted(parsed.flags),
            'options': {
                key: TelemetryRedactor.value(value) for key, value in parsed.options.items()
            },
            'args': TelemetryRedactor.value(parsed.rest),
            'started_at': self._started_at.isoformat(),
            'finished_at': datetime.now(UTC).isoformat(),
            'duration_ms': round((time.monotonic() - self._started) * self._MS_PER_SECOND),
            'outcome': outcome,
            'trace_id': format_trace_id(context.trace_id) if context.is_valid else None,
            'failure': FailureSnapshot.of(failure) if failure else None,
        }
