"""Self time per span: its duration minus the time its awaited children ran.

Summing a parent's and a child's latency counts the same wait twice. A span's
self time is what it spent on its own, so the slow span is the one with the
large self time. Concurrent children (task groups, gather) overlap, so the
parent loses the union of their intervals, not their sum. Fire-and-forget
work starts its own trace (`Work.detached`), so it takes nothing off the span
that spawned it. `span.self_time` pairs with the spanmetrics duration of the
same span name, which is the total.
"""

import threading
from typing import cast

from opentelemetry.context import Context
from opentelemetry.metrics import Meter
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.trace import SpanContext


class SelfTimeProcessor(SpanProcessor):
    NS_PER_MS = 1_000_000
    DEFAULT_KIND = 'io'
    BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000, 120000)

    def __init__(self, meter: Meter) -> None:
        self._histogram = meter.create_histogram(
            'span.self_time',
            unit='ms',
            description='Span duration minus the union of its awaited children',
            explicit_bucket_boundaries_advisory=self.BUCKETS_MS,
        )
        # Spans end on worker threads too (to_thread), so the open-span table is shared.
        self._lock = threading.Lock()
        self._children: dict[int, list[tuple[int, int]]] = {}

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        with self._lock:
            self._children[span.get_span_context().span_id] = []

    def on_end(self, span: ReadableSpan) -> None:
        kind = str((span.attributes or {}).get('work.kind', self.DEFAULT_KIND))
        start, end = span.start_time or 0, span.end_time or 0
        # The SDK gives every span a context; ReadableSpan just types it optional.
        own = cast('SpanContext', span.context)
        with self._lock:
            children = self._children.pop(own.span_id, [])
            # Only an open parent collects: a child outliving it would never be read.
            if span.parent:
                siblings = self._children.get(span.parent.span_id)
                if siblings is not None:
                    siblings.append((start, end))
        busy = self._union(children, start)
        self._histogram.record(
            (end - start - busy) / self.NS_PER_MS, {'span.name': span.name, 'work.kind': kind}
        )

    @staticmethod
    def _union(intervals: list[tuple[int, int]], parent_start: int) -> int:
        # Every child here ended while the parent was open, so only its start needs
        # clamping to the parent window.
        total, reached = 0, parent_start
        for child_start, child_end in sorted(intervals):
            start = max(child_start, reached)
            if child_end > start:
                total += child_end - start
                reached = child_end
        return total
