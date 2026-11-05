import contextlib

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from structlog.testing import capture_logs

from bot.domain.commands.base import Command, CommandConfig, ParsedCommand, Platform
from bot.domain.exceptions import BotError, ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


class _Echo(Command):
    def __init__(self, failure: Exception | None = None) -> None:
        super().__init__()
        self._failure = failure

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='eco')

    @property
    def menu_description(self) -> str:
        return 'Ecoa.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if self._failure:
            raise self._failure
        return []


@pytest.fixture
def spans(mocker):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    mocker.patch.object(Command, '_TRACER', provider.get_tracer('test'))
    return exporter


async def _run(failure: Exception | None = None, data: CommandData | None = None) -> None:
    data = data or GroupCommandDataFactory(text=',eco', platform=Platform.WHATSAPP)
    with contextlib.suppress(BotError, RuntimeError):
        await _Echo(failure).run(data)


class TestDimensions:
    @pytest.mark.anyio
    async def test_names_the_span_after_the_run(self, spans):
        await _run()

        assert spans.get_finished_spans()[0].name == 'command.run'

    @pytest.mark.anyio
    async def test_carries_the_command_name(self, spans):
        await _run()

        assert spans.get_finished_spans()[0].attributes['command.name'] == 'eco'

    @pytest.mark.anyio
    async def test_carries_the_platform(self, spans):
        data = PrivateCommandDataFactory(text=',eco', platform=Platform.TELEGRAM)

        await _run(data=data)

        assert spans.get_finished_spans()[0].attributes['platform'] == 'telegram'

    @pytest.mark.anyio
    async def test_platform_defaults_to_whatsapp(self, spans):
        await _run(data=GroupCommandDataFactory(text=',eco'))

        assert spans.get_finished_spans()[0].attributes['platform'] == 'whatsapp'

    @pytest.mark.anyio
    async def test_group_chat_type(self, spans):
        await _run()

        assert spans.get_finished_spans()[0].attributes['chat_type'] == 'group'

    @pytest.mark.anyio
    async def test_private_chat_type(self, spans):
        data = PrivateCommandDataFactory(text=',eco', platform=Platform.DISCORD)

        await _run(data=data)

        assert spans.get_finished_spans()[0].attributes['chat_type'] == 'private'


class TestOutcome:
    @pytest.mark.anyio
    async def test_success(self, spans):
        await _run()

        span = spans.get_finished_spans()[0]
        assert span.attributes['command.outcome'] == 'success'
        assert span.status.status_code is StatusCode.UNSET

    @pytest.mark.anyio
    async def test_bot_error_keeps_status_unset(self, spans):
        await _run(BotError('argumento inválido'))

        span = spans.get_finished_spans()[0]
        assert span.attributes['command.outcome'] == 'bot_error'
        assert span.status.status_code is StatusCode.UNSET

    @pytest.mark.anyio
    async def test_external_error_marks_error(self, spans):
        await _run(ExternalServiceError('api fora'))

        span = spans.get_finished_spans()[0]
        assert span.attributes['command.outcome'] == 'external_error'
        assert span.status.status_code is StatusCode.ERROR

    @pytest.mark.anyio
    async def test_unexpected_error_names_only_the_type(self, spans):
        await _run(RuntimeError('GET https://x.test/?api_key=secret'))

        span = spans.get_finished_spans()[0]
        assert span.attributes['command.outcome'] == 'unexpected_error'
        assert span.status.description == 'RuntimeError'
        assert not span.events

    @pytest.mark.anyio
    async def test_failure_still_reaches_the_caller(self, spans):
        command = _Echo(ExternalServiceError('api fora'))
        data = GroupCommandDataFactory(text=',eco', platform=Platform.WHATSAPP)

        with pytest.raises(ExternalServiceError):
            await command.run(data)


class TestCompletedEvent:
    @pytest.mark.anyio
    async def test_logs_one_completed_event_with_the_stable_fields(self, spans):
        data = GroupCommandDataFactory(text=',eco', platform=Platform.TELEGRAM)

        with capture_logs() as logs:
            await _run(data=data)

        [event] = [log for log in logs if log['event'] == 'command_completed']
        assert event['command'] == 'eco'
        assert event['platform'] == 'telegram'
        assert event['chat_type'] == 'group'
        assert event['chat'] == data.jid
        assert event['outcome'] == 'success'
        assert event['duration_ms'] >= 0
        assert event['log_level'] == 'info'

    @pytest.mark.anyio
    async def test_a_failure_logs_its_outcome_and_error_type(self, spans):
        with capture_logs() as logs:
            await _run(ExternalServiceError('https://x.test/?api_key=secret'))

        [event] = [log for log in logs if log['event'] == 'command_completed']
        assert event['outcome'] == 'external_error'
        assert event['error_type'] == 'ExternalServiceError'
        assert 'secret' not in str(event)
