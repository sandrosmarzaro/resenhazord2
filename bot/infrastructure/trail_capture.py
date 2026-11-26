"""Copies what a command emits into its open trail, through the field policy.

Both processors return at once outside a command, so the cost elsewhere is one
context-variable read per span or log line.
"""

from collections.abc import Iterable
from typing import Any, ClassVar

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.trace import format_span_id
from structlog.types import EventDict, WrappedLogger

from bot.infrastructure.command_trail import CommandTrail
from bot.infrastructure.telemetry_field_policy import TelemetryFieldPolicy
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


def _shown_fields(fields: Iterable[tuple[str, object]], limit: int) -> dict[str, str]:
    shown = ((key, TelemetryFieldPolicy.show(key, value)) for key, value in fields)
    kept = [(key, value) for key, value in shown if value is not None]
    return dict(kept[:limit])


class TrailSpanProcessor(SpanProcessor):
    MAX_ATTRIBUTES: ClassVar[int] = 12

    def on_end(self, span: ReadableSpan) -> None:
        trail = CommandTrail.current()
        if trail is None or span.context is None:
            return
        trail.spans.append(
            {
                'name': TelemetryRedactor.value(span.name),
                'span_id': format_span_id(span.context.span_id),
                'parent_id': format_span_id(span.parent.span_id) if span.parent else None,
                'start_ns': span.start_time,
                'end_ns': span.end_time,
                # Only the code: the description is free text, an exception message
                # at worst. The error type rides in the error.type attribute.
                'status': span.status.status_code.name,
                'attributes': _shown_fields((span.attributes or {}).items(), self.MAX_ATTRIBUTES),
            }
        )


class TrailLogProcessor:
    """A structlog processor: what Loki gets, the trail gets, minus debug lines."""

    MAX_FIELDS: ClassVar[int] = 12
    _SKIPPED_LEVEL: ClassVar[str] = 'debug'
    # Bound on every line of a WhatsApp command; the record already holds them once.
    _RECORD_FIELDS: ClassVar[frozenset[str]] = frozenset({'correlation_id', 'jid', 'sender'})

    def __call__(
        self, _logger: WrappedLogger, method_name: str, event_dict: EventDict
    ) -> EventDict:
        trail = CommandTrail.current()
        if trail is None or method_name == self._SKIPPED_LEVEL:
            return event_dict
        entry: dict[str, Any] = {
            'timestamp': event_dict.get('timestamp'),
            'level': event_dict.get('level', method_name),
            'event': TelemetryRedactor.value(event_dict.get('event')),
            'fields': _shown_fields(
                [
                    (key, value)
                    for key, value in event_dict.items()
                    if key not in self._RECORD_FIELDS
                ],
                self.MAX_FIELDS,
            ),
        }
        trail.logs.append(entry)
        return event_dict
