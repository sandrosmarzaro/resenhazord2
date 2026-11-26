import pytest
import structlog
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import StatusCode

from bot.domain.commands.base import Platform
from bot.infrastructure.command_trail import CommandTrail
from bot.infrastructure.telemetry_redactor import TelemetryRedactor
from bot.infrastructure.trail_capture import TrailLogProcessor, TrailSpanProcessor
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def tracer():
    provider = TracerProvider()
    provider.add_span_processor(TrailSpanProcessor())
    return provider.get_tracer('test')


@pytest.fixture
def data():
    return GroupCommandDataFactory(text=',moeda iene', platform=Platform.WHATSAPP)


async def _spans(tracer, data, emit) -> list[dict]:
    async with CommandTrail.open(data) as trail:
        emit(tracer)
        spans, _ = trail.spans.drain()
    return spans


async def _logs(data, emit) -> list[dict]:
    async with CommandTrail.open(data) as trail:
        emit()
        logs, _ = trail.logs.drain()
    return logs


def _log(method: str, **fields) -> dict:
    return TrailLogProcessor()(None, method, {'level': method, **fields})


class TestSpans:
    @pytest.mark.anyio
    async def test_captures_a_span_that_ends_in_the_command(self, tracer, data):
        def emit(tracer):
            with tracer.start_as_current_span('command.run'):
                pass

        [span] = await _spans(tracer, data, emit)

        assert span['name'] == 'command.run'

    @pytest.mark.anyio
    async def test_links_a_child_to_its_parent(self, tracer, data):
        def emit(tracer):
            with tracer.start_as_current_span('command.run'), tracer.start_as_current_span('GET'):
                pass

        child, parent = await _spans(tracer, data, emit)

        assert (child['parent_id'], parent['parent_id']) == (parent['span_id'], None)

    @pytest.mark.anyio
    async def test_keeps_the_timing(self, tracer, data):
        def emit(tracer):
            with tracer.start_as_current_span('command.run'):
                pass

        [span] = await _spans(tracer, data, emit)

        assert span['end_ns'] >= span['start_ns'] > 0

    @pytest.mark.anyio
    async def test_names_an_error_status(self, tracer, data):
        def emit(tracer):
            with tracer.start_as_current_span('command.run') as span:
                span.set_status(StatusCode.ERROR, 'HTTPStatusError')

        [span] = await _spans(tracer, data, emit)

        assert span['status'] == 'ERROR HTTPStatusError'

    @pytest.mark.anyio
    async def test_keeps_the_upstream_call_attributes(self, tracer, data):
        attributes = {'server.address': 'open.er-api.com', 'http.status_code': 200}

        def emit(tracer):
            with tracer.start_as_current_span('GET', attributes=attributes):
                pass

        [span] = await _spans(tracer, data, emit)

        assert span['attributes'] == {
            'server.address': 'open.er-api.com',
            'http.status_code': '200',
        }

    @pytest.mark.anyio
    async def test_drops_attributes_off_the_allowlist(self, tracer, data):
        def emit(tracer):
            with tracer.start_as_current_span('GET', attributes={'net.peer.ip': '10.0.0.1'}):
                pass

        [span] = await _spans(tracer, data, emit)

        assert span['attributes'] == {}

    @pytest.mark.anyio
    async def test_a_url_loses_its_credentials_and_query(self, tracer, data):
        url = 'https://user:p@ss@api.example.com:8443/v1/latest?apikey=abc#top'

        def emit(tracer):
            with tracer.start_as_current_span('GET', attributes={'http.url': url}):
                pass

        [span] = await _spans(tracer, data, emit)

        assert span['attributes'] == {'http.url': 'https://api.example.com:8443/v1/latest'}

    @pytest.mark.anyio
    async def test_a_url_path_token_is_redacted(self, tracer, data):
        url = 'https://api.telegram.org/bot123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw/getMe'

        def emit(tracer):
            with tracer.start_as_current_span('POST', attributes={'url.full': url}):
                pass

        [span] = await _spans(tracer, data, emit)

        assert span['attributes'] == {'url.full': 'https://api.telegram.org/bot<redacted>/getMe'}

    def test_a_span_outside_a_command_is_ignored(self, tracer):
        with tracer.start_as_current_span('heartbeat'):
            pass

        assert CommandTrail.current() is None


class TestLogs:
    @pytest.mark.anyio
    async def test_captures_a_log_line_of_the_command(self, data):
        [line] = await _logs(data, lambda: _log('info', event='command_completed'))

        assert (line['event'], line['level']) == ('command_completed', 'info')

    @pytest.mark.anyio
    async def test_keeps_the_fields(self, data):
        [line] = await _logs(
            data, lambda: _log('warning', event='upstream_failed', upstream='espn')
        )

        assert line['fields'] == {'upstream': 'espn'}

    @pytest.mark.anyio
    async def test_hashes_an_identity_field_whatever_its_shape(self, data):
        [line] = await _logs(data, lambda: _log('info', event='x', chat_id=-42))

        assert line['fields'] == {'chat_id': TelemetryRedactor.identity('-42')}

    @pytest.mark.anyio
    async def test_redacts_a_field_value(self, data):
        [line] = await _logs(data, lambda: _log('info', event='x', url='https://a.io/x?key=1'))

        assert line['fields'] == {'url': 'https://a.io/x?<redacted>'}

    @pytest.mark.anyio
    async def test_leaves_out_what_the_record_already_has(self, data):
        [line] = await _logs(
            data, lambda: _log('info', event='x', correlation_id='c', logger='bot')
        )

        assert line['fields'] == {}

    @pytest.mark.anyio
    async def test_skips_debug_lines_like_loki_does(self, data):
        assert await _logs(data, lambda: _log('debug', event='handle_raw')) == []

    def test_passes_the_event_on_unchanged(self):
        event = {'event': 'x', 'level': 'info'}

        assert TrailLogProcessor()(None, 'info', dict(event)) == event

    @pytest.mark.anyio
    async def test_reaches_structlog_lines(self, data):
        structlog.configure(
            processors=[TrailLogProcessor(), structlog.processors.KeyValueRenderer()]
        )
        try:
            [line] = await _logs(data, lambda: structlog.get_logger().info('agent_routing'))
        finally:
            structlog.reset_defaults()

        assert line['event'] == 'agent_routing'
