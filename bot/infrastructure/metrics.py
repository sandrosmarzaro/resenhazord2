"""Application metrics via the OTel meter.

Only the domain counters live here: retry and dead-letter events, which are
our own retry-ladder semantics (ADR 0004), not something any instrumentation
can derive. The RED metrics (rate/errors/duration) are derived from the
`command.handle` span by the spanmetrics connector in the core Alloy collector,
dimensioned by the `command.outcome` span attribute — so no manual counter or
histogram for those. The meter resolves to the global provider `init_otel`
installs (a proxy until then), so recording is a no-op when OTel is disabled.
"""

from opentelemetry import metrics

_meter = metrics.get_meter(__name__)

_retries = _meter.create_counter(
    'command.retries', unit='1', description='Command retries scheduled'
)
_dlq = _meter.create_counter(
    'command.dlq', unit='1', description='Commands dead-lettered after exhausting retries'
)


def record_retry() -> None:
    _retries.add(1)


def record_dlq() -> None:
    _dlq.add(1)
