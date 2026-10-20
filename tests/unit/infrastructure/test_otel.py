import pytest

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

