"""OpenTelemetry -> Grafana Cloud (LGTM) initialization.

Guarded on the OTLP endpoint the way Sentry is guarded on its DSN: an empty
endpoint installs no providers, so every OTel call stays a no-op. Traces,
metrics, and logs share one OTLP/HTTP endpoint and auth header; the HTTP
exporter needs the per-signal path (`/v1/traces` etc.) spelled out when the
endpoint is passed explicitly rather than read from the environment.
"""

import structlog
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from bot.settings import Settings

logger = structlog.get_logger()

_NAMESPACE = 'resenhazord2'
_NODE = 'core'


def init_otel(settings: Settings) -> None:
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip('/')
    if not endpoint:
        return

    headers = _parse_headers(settings.otel_exporter_otlp_headers)
    resource = Resource.create(
        {
            'service.name': settings.otel_service_name,
            'service.namespace': _NAMESPACE,
            'deployment.environment': _NODE,
        }
    )

    _init_traces(endpoint, headers, resource)
    _init_metrics(endpoint, headers, resource)
    _init_logs(endpoint, headers, resource)
    logger.info('otel_initialized', endpoint=endpoint, service=settings.otel_service_name)


def _init_traces(endpoint: str, headers: dict[str, str], resource: Resource) -> None:
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f'{endpoint}/v1/traces', headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def _init_metrics(endpoint: str, headers: dict[str, str], resource: Resource) -> None:
    exporter = OTLPMetricExporter(endpoint=f'{endpoint}/v1/metrics', headers=headers)
    reader = PeriodicExportingMetricReader(exporter)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))


def _init_logs(endpoint: str, headers: dict[str, str], resource: Resource) -> None:
    provider = LoggerProvider(resource=resource)
    exporter = OTLPLogExporter(endpoint=f'{endpoint}/v1/logs', headers=headers)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(provider)


def _parse_headers(raw: str) -> dict[str, str]:
    # OTEL_EXPORTER_OTLP_HEADERS form: comma-separated `key=value` pairs, e.g.
    # `Authorization=Basic <base64>`. The value itself never contains '='.
    headers: dict[str, str] = {}
    for pair in raw.split(','):
        key, sep, value = pair.partition('=')
        if sep and key.strip():
            headers[key.strip()] = value.strip()
    return headers
