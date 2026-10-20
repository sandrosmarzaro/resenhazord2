import httpx
import pytest
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from bot.infrastructure.otel import _parse_headers, init_otel
from bot.settings import Settings


@pytest.fixture
def otel_globals(mocker):
    return {
        name: mocker.patch(f'bot.infrastructure.otel.{name}')
        for name in (
            'trace.set_tracer_provider',
            'metrics.set_meter_provider',
            'set_logger_provider',
            'FastAPIInstrumentor',
            'HTTPXClientInstrumentor',
            'AioPikaInstrumentor',
            'LoggingHandler',
            'logging.getLogger',
        )
    }


@pytest.fixture
def otel_settings():
    return Settings(
        otel_exporter_otlp_endpoint='https://otlp.example/otlp',
        otel_exporter_otlp_headers='Authorization=Basic abc',
    )


class TestParseHeaders:
    def test_parses_authorization_basic_pair(self):
        headers = _parse_headers('Authorization=Basic dXNlcjpwYXNz')

        assert headers == {'Authorization': 'Basic dXNlcjpwYXNz'}

    def test_keeps_base64_padding_in_value(self):
        headers = _parse_headers('Authorization=Basic YWJjOjEyMw==')

        assert headers['Authorization'] == 'Basic YWJjOjEyMw=='

    def test_parses_multiple_comma_separated_pairs(self):
        headers = _parse_headers('Authorization=Basic abc,X-Scope-OrgID=1831737')

        assert headers == {'Authorization': 'Basic abc', 'X-Scope-OrgID': '1831737'}

    def test_empty_string_yields_no_headers(self):
        assert _parse_headers('') == {}


class TestInitOtel:
    def test_no_endpoint_is_a_noop(self, mocker):
        span_setter = mocker.patch('bot.infrastructure.otel.trace.set_tracer_provider')
        settings = Settings(otel_exporter_otlp_endpoint='')

        init_otel(settings, mocker.Mock())

        span_setter.assert_not_called()

    @pytest.mark.parametrize(
        'endpoint', ['https://otlp.example/otlp', 'https://otlp.example/otlp/']
    )
    def test_endpoint_installs_providers(self, mocker, otel_globals, endpoint):
        app = mocker.Mock()
        settings = Settings(
            otel_exporter_otlp_endpoint=endpoint,
            otel_exporter_otlp_headers='Authorization=Basic abc',
        )

        init_otel(settings, app)

        otel_globals['trace.set_tracer_provider'].assert_called_once()
        otel_globals['metrics.set_meter_provider'].assert_called_once()
        otel_globals['set_logger_provider'].assert_called_once()
        otel_globals['FastAPIInstrumentor'].instrument_app.assert_called_once_with(app)

    def test_bridges_stdlib_logging_into_otel(self, mocker, otel_globals, otel_settings):
        root = mocker.patch('bot.infrastructure.otel.logging.getLogger').return_value

        init_otel(otel_settings, mocker.Mock())

        root.addHandler.assert_called_once_with(otel_globals['LoggingHandler'].return_value)


class TestHttpxSpans:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('url', 'expected'),
        [
            (
                'https://api.telegram.org/bot123456:AAsecret-Token_x/getUpdates',
                'https://api.telegram.org/bot<redacted>/getUpdates',
            ),
            ('https://api.example.com/v1/items', 'https://api.example.com/v1/items'),
        ],
    )
    async def test_span_url_hides_telegram_bot_token(
        self, mocker, otel_globals, otel_settings, url, expected
    ):
        init_otel(otel_settings, mocker.Mock())
        instrument = otel_globals['HTTPXClientInstrumentor'].return_value.instrument
        async_hook = instrument.call_args.kwargs.get('async_request_hook')
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        transport = httpx.MockTransport(lambda _: httpx.Response(200))

        async with httpx.AsyncClient(transport=transport) as client:
            HTTPXClientInstrumentor.instrument_client(
                client, tracer_provider=provider, request_hook=async_hook
            )
            await client.post(url)

        [span] = exporter.get_finished_spans()
        assert span.attributes['http.url'] == expected
