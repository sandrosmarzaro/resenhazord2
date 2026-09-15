import pytest

from bot.infrastructure.otel import _parse_headers, init_otel
from bot.settings import Settings


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
    def test_endpoint_installs_providers(self, mocker, endpoint):
        span_setter = mocker.patch('bot.infrastructure.otel.trace.set_tracer_provider')
        meter_setter = mocker.patch('bot.infrastructure.otel.metrics.set_meter_provider')
        log_setter = mocker.patch('bot.infrastructure.otel.set_logger_provider')
        fastapi_inst = mocker.patch('bot.infrastructure.otel.FastAPIInstrumentor')
        mocker.patch('bot.infrastructure.otel.HTTPXClientInstrumentor')
        mocker.patch('bot.infrastructure.otel.AioPikaInstrumentor')
        app = mocker.Mock()
        settings = Settings(
            otel_exporter_otlp_endpoint=endpoint,
            otel_exporter_otlp_headers='Authorization=Basic abc',
        )

        init_otel(settings, app)

        span_setter.assert_called_once()
        meter_setter.assert_called_once()
        log_setter.assert_called_once()
        fastapi_inst.instrument_app.assert_called_once_with(app)
