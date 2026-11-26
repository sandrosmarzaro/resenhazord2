import contextlib
from pathlib import Path

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from bot.domain.commands.base import Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.exceptions import BotError, ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.command_trail import CommandTrail
from bot.infrastructure.failure_snapshot import FailureSnapshot
from tests.factories.command_data import GroupCommandDataFactory


class _Quote(Command):
    def __init__(self, failure: Exception | None = None) -> None:
        super().__init__()
        self._failure = failure

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='moeda', flags=[Flag.DM])

    @property
    def menu_description(self) -> str:
        return 'Cota.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if self._failure:
            self._fetch(parsed.rest, api_key='abc123secret', data=data)
        return []

    def _fetch(self, currency: str, api_key: str, data: CommandData | None = None) -> None:
        raise self._failure


async def _execution(failure: Exception | None = None, text: str = ',moeda dm iene') -> dict:
    data = GroupCommandDataFactory(text=text, platform=Platform.WHATSAPP)
    async with CommandTrail.open(data) as trail:
        with contextlib.suppress(Exception):
            await _Quote(failure).run(data)
        return trail.execution


@pytest.fixture
def tracer(mocker):
    tracer = TracerProvider().get_tracer('test')
    mocker.patch.object(Command, '_TRACER', tracer)
    return tracer


class TestWhatRan:
    @pytest.mark.anyio
    async def test_names_the_command(self):
        assert (await _execution())['command'] == 'moeda'

    @pytest.mark.anyio
    async def test_keeps_the_text_and_its_parse(self):
        execution = await _execution()

        assert (execution['text'], execution['flags'], execution['args']) == (
            ',moeda dm iene',
            ['dm'],
            'iene',
        )

    @pytest.mark.anyio
    async def test_hashes_a_phone_in_the_text(self):
        execution = await _execution(text=',moeda 5511999999999')

        assert '5511999999999' not in str(execution)

    @pytest.mark.anyio
    async def test_times_the_run(self):
        execution = await _execution()

        assert execution['finished_at'] >= execution['started_at']

    @pytest.mark.anyio
    async def test_a_success_has_no_failure(self):
        execution = await _execution()

        assert (execution['outcome'], execution['failure']) == ('success', None)

    @pytest.mark.anyio
    async def test_keeps_the_trace_id(self, tracer):
        execution = await _execution()

        assert len(execution['trace_id']) == 32

    @pytest.mark.anyio
    async def test_without_tracing_there_is_no_trace_id(self, mocker):
        mocker.patch.object(Command, '_TRACER', trace.NoOpTracer())

        assert (await _execution())['trace_id'] is None

    @pytest.mark.anyio
    async def test_nothing_is_noted_without_a_trail(self):
        data = GroupCommandDataFactory(text=',moeda', platform=Platform.WHATSAPP)

        await _Quote().run(data)

        assert CommandTrail.current() is None


class TestFailure:
    @pytest.fixture(autouse=True)
    def _tests_count_as_bot_code(self, mocker):
        mocker.patch.object(FailureSnapshot, '_BOT_ROOT', str(Path(__file__).resolve().parents[3]))

    @pytest.mark.anyio
    async def test_classifies_the_outcome(self):
        execution = await _execution(ExternalServiceError('Sem cotação'))

        assert execution['outcome'] == 'external_error'

    @pytest.mark.anyio
    async def test_a_bot_error_is_kept_too(self):
        execution = await _execution(BotError('Moeda inválida'))

        assert (execution['outcome'], execution['failure']['type']) == ('bot_error', 'BotError')

    @pytest.mark.anyio
    async def test_keeps_the_type_and_message(self):
        failure = (await _execution(RuntimeError('boom')))['failure']

        assert (failure['type'], failure['message']) == ('RuntimeError', 'boom')

    @pytest.mark.anyio
    async def test_keeps_the_stack_trace(self):
        failure = (await _execution(RuntimeError('boom')))['failure']

        assert 'in _fetch' in failure['stack']

    @pytest.mark.anyio
    async def test_redacts_the_message(self):
        failure = (await _execution(RuntimeError('GET https://a.io/x?token=abc')))['failure']

        assert 'abc' not in failure['message'] + failure['stack']

    @pytest.mark.anyio
    async def test_shows_the_failing_frame(self):
        frame = (await _execution(RuntimeError('boom')))['failure']['frame']

        assert frame['function'] == '_Quote._fetch'

    @pytest.mark.anyio
    async def test_shows_the_frame_arguments_redacted(self):
        frame = (await _execution(RuntimeError('boom')))['failure']['frame']

        assert (frame['arguments']['currency'], frame['arguments']['api_key']) == (
            'iene',
            '<redacted>',
        )

    @pytest.mark.anyio
    async def test_an_object_argument_shows_only_its_type(self):
        frame = (await _execution(RuntimeError('boom')))['failure']['frame']

        assert frame['arguments']['data'] == '<CommandData>'

    @pytest.mark.anyio
    async def test_a_failure_outside_bot_code_has_no_frame(self, mocker):
        mocker.patch.object(FailureSnapshot, '_BOT_ROOT', '/nowhere')

        assert (await _execution(RuntimeError('boom')))['failure']['frame'] is None
