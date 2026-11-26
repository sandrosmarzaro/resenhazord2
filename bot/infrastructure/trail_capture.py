"""Copies what a command emits into its open trail, redacted on the way in.

Both processors return at once outside a command, so the cost elsewhere is one
context-variable read per span or log line.
"""

from typing import Any, ClassVar
from urllib.parse import urlsplit

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.trace import format_span_id
from structlog.types import EventDict, WrappedLogger

from bot.data.telemetry_privacy import (
    IDENTITY_LOG_FIELDS,
    KEPT_SPAN_ATTRIBUTES,
    OMITTED_LOG_FIELDS,
)
from bot.infrastructure.command_trail import CommandTrail
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class TrailSpanProcessor(SpanProcessor):
    _URL_ATTRIBUTES: ClassVar[frozenset[str]] = frozenset({'http.url', 'url.full'})

    def on_end(self, span: ReadableSpan) -> None:
        trail = CommandTrail.current()
        if trail is None or span.context is None:
            return
        status = span.status
        trail.spans.append(
            {
                'name': span.name,
                'span_id': format_span_id(span.context.span_id),
                'parent_id': format_span_id(span.parent.span_id) if span.parent else None,
                'start_ns': span.start_time,
                'end_ns': span.end_time,
                'status': ' '.join(filter(None, (status.status_code.name, status.description))),
                'attributes': {
                    key: self._attribute(key, value)
                    for key, value in (span.attributes or {}).items()
                    if key in KEPT_SPAN_ATTRIBUTES
                },
            }
        )

    @classmethod
    def _attribute(cls, key: str, value: object) -> str:
        if key not in cls._URL_ATTRIBUTES:
            return TelemetryRedactor.value(value)
        # An allowlist, not a pattern: no userinfo, query string or fragment survives.
        url = urlsplit(str(value))
        host = url.hostname or ''
        netloc = f'{host}:{url.port}' if url.port else host
        return TelemetryRedactor.value(url._replace(netloc=netloc, query='', fragment='').geturl())


class TrailLogProcessor:
    """A structlog processor: what Loki gets, the trail gets, minus debug lines."""

    MAX_FIELDS: ClassVar[int] = 12
    _SKIPPED_LEVEL: ClassVar[str] = 'debug'

    def __call__(
        self, _logger: WrappedLogger, method_name: str, event_dict: EventDict
    ) -> EventDict:
        trail = CommandTrail.current()
        if trail is None or method_name == self._SKIPPED_LEVEL:
            return event_dict
        trail.logs.append(
            {
                'timestamp': event_dict.get('timestamp'),
                'level': event_dict.get('level', method_name),
                'event': TelemetryRedactor.value(event_dict.get('event')),
                'fields': self._fields(event_dict),
            }
        )
        return event_dict

    @classmethod
    def _fields(cls, event_dict: EventDict) -> dict[str, Any]:
        kept = [(key, value) for key, value in event_dict.items() if key not in OMITTED_LOG_FIELDS]
        return {key: cls._field(key, value) for key, value in kept[: cls.MAX_FIELDS]}

    @staticmethod
    def _field(key: str, value: object) -> str:
        # An id is hashed whole by its field name: a Telegram or Discord id is too short
        # for the text patterns to tell it from any other number.
        if key in IDENTITY_LOG_FIELDS:
            return TelemetryRedactor.identity(str(value))
        return TelemetryRedactor.value(value)
