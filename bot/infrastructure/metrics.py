"""Application metrics via the OTel meter.

Only the domain counters live here: retry and dead-letter events, which are
our own retry-ladder semantics (ADR 0004), not something any instrumentation
can derive. The RED metrics (rate/errors/duration) are derived from the
`command.handle` span by the spanmetrics connector in the core Alloy collector,
dimensioned by the `command.outcome` span attribute — so no manual counter or
histogram for those. The meter resolves to the global provider `init_otel`
installs (a proxy until then), so recording is a no-op when OTel is disabled.
"""

from opentelemetry import metrics, trace

_meter = metrics.get_meter(__name__)

_retries = _meter.create_counter(
    'command.retries', unit='1', description='Command retries scheduled'
)
_dlq = _meter.create_counter(
    'command.dlq', unit='1', description='Commands dead-lettered after exhausting retries'
)
# The agent's NL->command mapping is not a broker command span, so its RED
# metrics can't be derived by the spanmetrics connector. This counter carries
# the outcome, provider, and prompt version so Grafana can chart which prompt
# version and provider produce which mapping outcomes.
_agent_mappings = _meter.create_counter(
    'agent.mappings', unit='1', description='Agent natural-language to command mappings'
)


def record_retry() -> None:
    _retries.add(1)


def record_dlq() -> None:
    _dlq.add(1)


def record_agent_mapping(outcome: str, provider: str, prompt_version: str) -> None:
    dimensions = {
        'agent.outcome': outcome,
        'agent.provider': provider,
        'agent.prompt.version': prompt_version,
    }
    _agent_mappings.add(1, dimensions)
    # Stamp the same dimensions on the enclosing command.handle span so a single
    # trace can be tied to the prompt version and outcome that produced it.
    span = trace.get_current_span()
    for key, value in dimensions.items():
        span.set_attribute(key, value)
