"""W3C trace-context propagation across the RabbitMQ envelope.

The command flow crosses the broker (edge gateway -> core bot), not HTTP, so
the trace is carried as a `traceparent` field inside the message envelope
rather than in AMQP or HTTP headers. Inject writes the active span's context
into the outgoing carrier; extract reads it back so the consuming side
continues the same trace. The gateway (Bun) mirrors this on its side (PRD
Phase 4); until then, and whenever OTel is disabled, inject writes nothing and
extract yields a fresh root context.
"""

from typing import Any

from opentelemetry.context import Context
from opentelemetry.propagate import extract, inject


def inject_trace_context(carrier: dict[str, Any]) -> None:
    inject(carrier)


def extract_trace_context(carrier: dict[str, Any]) -> Context:
    return extract(carrier)
