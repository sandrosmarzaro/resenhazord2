from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.util.re import parse_env_headers

from bot.settings import Settings


def publish_gauge(name: str, value: float, attributes: dict[str, str]) -> None:
    # The eval runs in CI, away from the bot's collector, so it pushes straight to
    # the same OTLP endpoint. No endpoint (a local run) publishes nothing.
    settings = Settings()
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip('/')
    if not endpoint:
        return
    exporter = OTLPMetricExporter(
        endpoint=f'{endpoint}/v1/metrics',
        headers=parse_env_headers(settings.otel_exporter_otlp_headers, liberal=True),
    )
    # A fixed instance keeps every CI run on one series instead of one per process.
    resource = Resource.create(
        {
            'service.name': 'prompt-eval',
            'service.namespace': 'resenhazord2',
            'service.instance.id': 'ci',
        }
    )
    provider = MeterProvider(
        resource=resource, metric_readers=[PeriodicExportingMetricReader(exporter)]
    )
    provider.get_meter(__name__).create_gauge(name).set(value, attributes)
    # Shutting down flushes the one reading before the test process exits.
    provider.shutdown()
