import asyncio
import base64
import json

import pytest
import sentry_sdk
from fakeredis.aioredis import FakeRedis
from structlog.testing import capture_logs

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.domain.commands.base import CommandConfig, Platform
from bot.domain.exceptions import BotError, DownloadError, ExternalServiceError, ValidationError
from bot.domain.models.command_data import CommandData
from bot.domain.models.contents.image_content import ImageBufferContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from bot.infrastructure.command_inbox import RedisCommandInbox
from tests.fixtures.mock_broker import MockBrokerPort


def _envelope(
    text: str, jid: str = 'g@g.us', attempts: int | None = None, message_id: str | None = None
) -> bytes:
    payload: dict = {
        'id': 'corr-1',
        'data': {
            'text': text,
            'jid': jid,
            'sender_jid': 'u@s.whatsapp.net',
            'message_id': message_id,
        },
    }
    if attempts is not None:
        payload['attempts'] = attempts
    return json.dumps(payload).encode()


def _queues(broker: MockBrokerPort) -> list[str]:
    return [queue for queue, _ in broker.published]


def _exhausted_logs(logs: list[dict]) -> list[dict]:
    return [
        {key: log[key] for key in ('log_level', 'attempts', 'error')}
        for log in logs
        if log['event'] == 'command_retries_exhausted'
    ]


class TestDispatch:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_runs_handler_with_command_data_from_envelope(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        consumer = CommandConsumer(broker, handler)
        await consumer.start()

        await broker.deliver('commands', _envelope('ping'))

        passed = handler.handle.await_args.args[0]
        assert passed.text == 'ping'
        assert passed.jid == 'g@g.us'

    @pytest.mark.anyio
    async def test_publishes_reply_to_replies_queue(self, mocker):
        broker = MockBrokerPort()
        message = BotMessage(jid='g@g.us', content=TextContent('pong'))
        handler = mocker.AsyncMock()
        handler.handle.return_value = [message]
        consumer = CommandConsumer(broker, handler)
        await consumer.start()

        await broker.deliver('commands', _envelope('ping'))

        queue, body = broker.published[0]
        reply = json.loads(body)
        assert queue == 'replies'
        assert reply == {'id': 'corr-1', 'messages': [message.to_dict()]}


class TestMediaReply:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_inlines_buffer_content_as_base64(self, mocker):
        broker = MockBrokerPort()
        message = BotMessage(jid='g@g.us', content=ImageBufferContent(b'\x01\x02\x03'))
        handler = mocker.AsyncMock()
        handler.handle.return_value = [message]
        consumer = CommandConsumer(broker, handler)
        await consumer.start()

        await broker.deliver('commands', _envelope('ping'))

        _, body = broker.published[0]
        content = json.loads(body)['messages'][0]['content']
        assert content['type'] == 'image_buffer'
        assert content['buffer_b64'] == base64.b64encode(b'\x01\x02\x03').decode()


class TestRetry:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_external_error_schedules_a_retry(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ExternalServiceError('api down')
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        queue, body = broker.published[0]
        assert queue == 'commands.retry'
        assert json.loads(body)['attempts'] == 1
        assert 'replies' not in _queues(broker)

    @pytest.mark.anyio
    async def test_exhausted_retries_go_to_dlq_with_error_reply(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ExternalServiceError('still down')
        await CommandConsumer(broker, handler).start()

        await broker.deliver(
            'commands', _envelope('ping', attempts=CommandConsumer.MAX_ATTEMPTS - 1)
        )

        queues = _queues(broker)
        assert 'commands.dlq' in queues
        assert 'replies' in queues
        assert 'commands.retry' not in queues

    @pytest.mark.anyio
    async def test_download_error_skips_the_retry_ladder(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = DownloadError('video gone')
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        queues = _queues(broker)
        assert 'commands.dlq' in queues
        assert 'commands.retry' not in queues

    @pytest.mark.anyio
    async def test_download_error_dlq_logs_at_warning(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = DownloadError('video gone')
        await CommandConsumer(broker, handler).start()

        with capture_logs() as logs:
            await broker.deliver('commands', _envelope('ping'))

        assert _exhausted_logs(logs) == [
            {'log_level': 'warning', 'attempts': 1, 'error': 'video gone'}
        ]
        assert [log for log in logs if log['log_level'] == 'error'] == []

    @pytest.mark.anyio
    async def test_exhausted_external_error_dlq_logs_at_error(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ExternalServiceError('still down')
        await CommandConsumer(broker, handler).start()

        with capture_logs() as logs:
            await broker.deliver(
                'commands', _envelope('ping', attempts=CommandConsumer.MAX_ATTEMPTS - 1)
            )

        assert _exhausted_logs(logs) == [
            {'log_level': 'error', 'attempts': CommandConsumer.MAX_ATTEMPTS, 'error': 'still down'}
        ]

    @pytest.mark.anyio
    async def test_validation_error_replies_without_retry(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ValidationError('bad input')
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        assert _queues(broker) == ['replies']


class TestErrors:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_bot_error_publishes_user_message_reply(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = BotError('nope')
        consumer = CommandConsumer(broker, handler)
        await consumer.start()

        await broker.deliver('commands', _envelope('ping'))

        _, body = broker.published[0]
        reply = json.loads(body)
        assert reply['messages'][0]['content']['text'] == 'nope'

    @pytest.mark.anyio
    async def test_unexpected_error_publishes_generic_error_reply(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = NotImplementedError('download_media unsupported')
        consumer = CommandConsumer(broker, handler)
        await consumer.start()

        await broker.deliver('commands', _envelope('ping'))

        _, body = broker.published[0]
        reply = json.loads(body)
        assert reply['messages'][0]['content']['text'] == 'Ocorreu um erro ao executar o comando.'

    @pytest.mark.anyio
    async def test_no_match_publishes_empty_terminal_reply(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = None
        consumer = CommandConsumer(broker, handler)
        await consumer.start()

        await broker.deliver('commands', _envelope('ping'))

        _, body = broker.published[0]
        assert json.loads(body) == {'id': 'corr-1', 'messages': []}


def _event_tags() -> dict:
    return sentry_sdk.get_isolation_scope().apply_to_event({}, {}).get('tags') or {}


class TestSentryScope:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_tags_events_raised_while_handling_with_the_correlation_id(self, mocker):
        seen: list[dict] = []

        async def handle(_, *, on_match):
            seen.append(_event_tags())
            return []

        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = handle
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        assert seen[0]['correlation_id'] == 'corr-1'

    @pytest.mark.anyio
    async def test_correlation_tag_does_not_outlive_the_command(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        assert 'correlation_id' not in _event_tags()


class TestTracePropagation:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_extracts_parent_context_from_envelope(self, mocker):
        extract = mocker.patch('bot.adapters.broker.command_consumer.extract_trace_context')
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        extract.assert_called_once()
        assert extract.call_args.args[0]['id'] == 'corr-1'

    @pytest.mark.anyio
    async def test_injects_trace_context_into_reply(self, mocker):
        inject = mocker.patch('bot.adapters.broker.command_consumer.inject_trace_context')
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        inject.assert_called_once()
        assert 'messages' in inject.call_args.args[0]


class TestMetrics:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @staticmethod
    def _span(mocker):
        tracer = mocker.patch('bot.adapters.broker.command_consumer._tracer')
        return tracer.start_as_current_span.return_value.__enter__.return_value

    @pytest.mark.anyio
    async def test_success_tags_span_with_success_outcome(self, mocker):
        span = self._span(mocker)
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        span.set_attribute.assert_called_once_with('command.outcome', 'success')

    @pytest.mark.anyio
    async def test_bot_error_tags_span_with_bot_error_outcome(self, mocker):
        span = self._span(mocker)
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = BotError('nope')
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        span.set_attribute.assert_called_once_with('command.outcome', 'bot_error')

    @pytest.mark.anyio
    async def test_unexpected_error_tags_span_with_unexpected_error_outcome(self, mocker):
        span = self._span(mocker)
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = NotImplementedError('download_media unsupported')
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        span.set_attribute.assert_called_once_with('command.outcome', 'unexpected_error')

    @pytest.mark.anyio
    async def test_scheduled_retry_tags_external_outcome_and_counts_retry(self, mocker):
        span = self._span(mocker)
        retries = mocker.patch('bot.infrastructure.metrics._retries')
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ExternalServiceError('api down')
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        span.set_attribute.assert_called_once_with('command.outcome', 'external_error')
        retries.add.assert_called_once_with(1)

    @pytest.mark.anyio
    async def test_counts_the_delivery_in_flight_until_it_is_answered(self, mocker):
        self._span(mocker)
        in_flight = mocker.patch('bot.infrastructure.metrics._in_flight')
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', _envelope('ping'))

        assert [call.args for call in in_flight.add.call_args_list] == [(1,), (-1,)]

    @pytest.mark.anyio
    async def test_exhausted_retries_count_dlq(self, mocker):
        self._span(mocker)
        dlq = mocker.patch('bot.infrastructure.metrics._dlq')
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ExternalServiceError('still down')
        await CommandConsumer(broker, handler).start()

        await broker.deliver(
            'commands', _envelope('ping', attempts=CommandConsumer.MAX_ATTEMPTS - 1)
        )

        dlq.add.assert_called_once_with(1)


class TestRedelivery:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.fixture
    def inbox(self):
        return RedisCommandInbox(FakeRedis())

    @pytest.mark.anyio
    async def test_redelivered_command_is_skipped(self, mocker, inbox):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler, inbox).start()
        body = _envelope('ping', message_id='MSG-1')

        await broker.deliver('commands', body)
        await broker.deliver('commands', body)

        assert handler.handle.await_count == 1
        assert _queues(broker) == ['replies']

    @pytest.mark.anyio
    async def test_scheduled_retry_still_runs(self, mocker, inbox):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = [ExternalServiceError('api down'), []]
        await CommandConsumer(broker, handler, inbox).start()
        await broker.deliver('commands', _envelope('ping', message_id='MSG-1'))
        _, retry_body = broker.published[0]

        await broker.deliver('commands', retry_body)

        assert handler.handle.await_count == 2

    @pytest.mark.anyio
    async def test_command_without_message_id_always_runs(self, mocker, inbox):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler, inbox).start()
        body = _envelope('ping')

        await broker.deliver('commands', body)
        await broker.deliver('commands', body)

        assert handler.handle.await_count == 2

    @pytest.mark.anyio
    async def test_same_message_id_in_another_chat_runs(self, mocker, inbox):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler, inbox).start()

        await broker.deliver('commands', _envelope('ping', jid='a@g.us', message_id='MSG-1'))
        await broker.deliver('commands', _envelope('ping', jid='b@g.us', message_id='MSG-1'))

        assert handler.handle.await_count == 2

    @pytest.mark.anyio
    async def test_replayed_dead_letter_runs_again(self, mocker, inbox):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = [ExternalServiceError('still down'), []]
        await CommandConsumer(broker, handler, inbox).start()
        body = _envelope('ping', attempts=CommandConsumer.MAX_ATTEMPTS - 1, message_id='MSG-1')
        await broker.deliver('commands', body)
        replayed = {**json.loads(body), 'attempts': 0, 'replayed': True}

        await broker.deliver('commands', json.dumps(replayed).encode())

        assert handler.handle.await_count == 2


class _HeldHandler:
    """Keeps every command running until released, to deliver another one meanwhile."""

    def __init__(self) -> None:
        self.runs = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def handle(self, data, *, on_match):
        self.runs += 1
        self.started.set()
        await self.release.wait()
        return []


class TestConcurrentDelivery:
    # Long enough for a skipped delivery to finish, short enough to fail fast when it doesn't.
    SKIP_DEADLINE_SECONDS = 0.05
    BOTH_RAN = 2

    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.fixture
    def inbox(self):
        return RedisCommandInbox(FakeRedis())

    async def _deliver_while_running(
        self, broker: MockBrokerPort, handler: _HeldHandler, first: bytes, second: bytes
    ) -> None:
        running = asyncio.create_task(broker.deliver('commands', first))
        await handler.started.wait()
        duplicate = asyncio.create_task(broker.deliver('commands', second))
        await asyncio.wait({duplicate}, timeout=self.SKIP_DEADLINE_SECONDS)
        handler.release.set()
        await asyncio.gather(running, duplicate)

    @pytest.mark.anyio
    async def test_same_message_while_running_runs_and_replies_once(self, inbox):
        broker = MockBrokerPort()
        handler = _HeldHandler()
        await CommandConsumer(broker, handler, inbox).start()
        body = _envelope('ping', message_id='MSG-1')

        await self._deliver_while_running(broker, handler, body, body)

        assert handler.runs == 1
        assert _queues(broker) == ['replies']

    @pytest.mark.anyio
    async def test_commands_without_message_id_both_run(self, inbox):
        broker = MockBrokerPort()
        handler = _HeldHandler()
        await CommandConsumer(broker, handler, inbox).start()
        body = _envelope('ping')

        await self._deliver_while_running(broker, handler, body, body)

        assert handler.runs == self.BOTH_RAN

    @pytest.mark.anyio
    async def test_same_id_in_another_chat_runs_while_the_first_runs(self, inbox):
        broker = MockBrokerPort()
        handler = _HeldHandler()
        await CommandConsumer(broker, handler, inbox).start()
        first = _envelope('ping', jid='a@g.us', message_id='MSG-1')
        second = _envelope('ping', jid='b@g.us', message_id='MSG-1')

        await self._deliver_while_running(broker, handler, first, second)

        assert handler.runs == self.BOTH_RAN

    @pytest.mark.anyio
    async def test_redelivery_after_a_crash_runs_on_the_restarted_consumer(self, inbox):
        crashed_broker = MockBrokerPort()
        crashed_handler = _HeldHandler()
        await CommandConsumer(crashed_broker, crashed_handler, inbox).start()
        body = _envelope('ping', message_id='MSG-1')
        running = asyncio.create_task(crashed_broker.deliver('commands', body))
        await crashed_handler.started.wait()
        running.cancel()
        await asyncio.wait({running})
        broker = MockBrokerPort()
        handler = _HeldHandler()
        handler.release.set()
        await CommandConsumer(broker, handler, inbox).start()

        await broker.deliver('commands', body)

        assert handler.runs == 1
        assert _queues(broker) == ['replies']

    @pytest.mark.anyio
    async def test_message_runs_again_once_a_failed_run_let_it_go(self, inbox):
        broker = MockBrokerPort()
        handler = _HeldHandler()
        await CommandConsumer(broker, handler, inbox).start()
        body = _envelope('ping', message_id='MSG-1')
        running = asyncio.create_task(broker.deliver('commands', body))
        await handler.started.wait()
        running.cancel()
        await asyncio.wait({running})
        handler.release.set()

        await broker.deliver('commands', body)

        assert handler.runs == self.BOTH_RAN


class _LaneHandler:
    """Records how many replies were already out when each command started running."""

    def __init__(self, broker: MockBrokerPort, mocker, *, exclusive: bool) -> None:
        self._broker = broker
        self._command = mocker.Mock(config=CommandConfig(name='dl', exclusive=exclusive))
        self.replies_out_at_start: dict[str, int] = {}

    async def handle(self, data, *, on_match):
        await on_match(self._command)
        self.replies_out_at_start[data.text] = len(self._broker.published)
        await asyncio.sleep(0)  # simulated work: lets the other delivery interleave
        if data.text == 'boom':
            message = 'falhou'
            raise BotError(message)
        return []


class TestExclusiveLane:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    async def _deliver_together(self, broker: MockBrokerPort, *texts: str) -> None:
        await asyncio.gather(*(broker.deliver('commands', _envelope(text)) for text in texts))

    @pytest.mark.anyio
    async def test_exclusive_commands_run_one_at_a_time_until_replied(self, mocker):
        broker = MockBrokerPort()
        handler = _LaneHandler(broker, mocker, exclusive=True)
        await CommandConsumer(broker, handler).start()

        await self._deliver_together(broker, 'first', 'second')

        assert handler.replies_out_at_start == {'first': 0, 'second': 1}

    @pytest.mark.anyio
    async def test_other_commands_run_side_by_side(self, mocker):
        broker = MockBrokerPort()
        handler = _LaneHandler(broker, mocker, exclusive=False)
        await CommandConsumer(broker, handler).start()

        await self._deliver_together(broker, 'first', 'second')

        assert handler.replies_out_at_start == {'first': 0, 'second': 0}

    @pytest.mark.anyio
    async def test_times_the_wait_for_the_lane_of_each_exclusive_command(self, mocker):
        lane_wait = mocker.patch('bot.infrastructure.metrics._lane_wait')
        broker = MockBrokerPort()
        handler = _LaneHandler(broker, mocker, exclusive=True)
        await CommandConsumer(broker, handler).start()

        await self._deliver_together(broker, 'first', 'second')

        waits = [call.args[0] for call in lane_wait.record.call_args_list]
        assert len(waits) == 2
        assert all(wait >= 0 for wait in waits)

    @pytest.mark.anyio
    async def test_other_commands_never_wait_for_the_lane(self, mocker):
        lane_wait = mocker.patch('bot.infrastructure.metrics._lane_wait')
        broker = MockBrokerPort()
        handler = _LaneHandler(broker, mocker, exclusive=False)
        await CommandConsumer(broker, handler).start()

        await self._deliver_together(broker, 'first', 'second')

        lane_wait.record.assert_not_called()

    @pytest.mark.anyio
    async def test_a_failed_exclusive_command_frees_the_lane(self, mocker):
        broker = MockBrokerPort()
        handler = _LaneHandler(broker, mocker, exclusive=True)
        await CommandConsumer(broker, handler).start()

        await self._deliver_together(broker, 'boom', 'second')

        assert handler.replies_out_at_start == {'boom': 0, 'second': 1}


_TRACE_ID = '0af7651916cd43dd8448eb211c80319c'
_TRACEPARENT = f'00-{_TRACE_ID}-b7ad6b7169203331-01'
_FULL_PAYLOAD = {
    'text': ',sticker',
    'jid': 'g@g.us',
    'sender_jid': 'u@s.whatsapp.net',
    'participant': 'p@s.whatsapp.net',
    'is_group': True,
    'expiration': 86400,
    'mentioned_jids': ['m@s.whatsapp.net'],
    'quoted_message_id': 'Q-1',
    'quoted_text': 'quoted',
    'media_type': 'image',
    'media_source': 'quoted',
    'media_is_animated': True,
    'media_caption': 'caption',
    'media_buffer_b64': base64.b64encode(b'media').decode(),
    'message_id': 'MSG-1',
    'push_name': 'Fulano',
}


def _full_envelope(**extra: object) -> dict:
    return {'id': 'corr-1', 'traceparent': _TRACEPARENT, 'data': _FULL_PAYLOAD, **extra}


class _RecordingInbox:
    """Records which queues had a publish when each message was marked answered."""

    def __init__(self, broker: MockBrokerPort) -> None:
        self._broker = broker
        self.marked: list[tuple[str, list[str]]] = []

    async def is_done(self, key: str) -> bool:
        return False

    async def mark_done(self, key: str) -> None:
        self.marked.append((key, _queues(self._broker)))


class TestQueueContract:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_declares_the_publish_targets_and_consumes_commands(self, mocker):
        broker = MockBrokerPort()

        await CommandConsumer(broker, mocker.AsyncMock()).start()

        assert broker.declared == ['replies', 'commands.dlq', 'commands.retry']
        assert broker.retry_queues == [('commands.retry', 30_000, 'commands')]

    @pytest.mark.anyio
    async def test_maps_every_payload_field_into_command_data(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', json.dumps(_full_envelope()).encode())

        assert handler.handle.await_args.args[0] == CommandData(
            text=',sticker',
            jid='g@g.us',
            sender_jid='u@s.whatsapp.net',
            participant='p@s.whatsapp.net',
            is_group=True,
            expiration=86400,
            mentioned_jids=['m@s.whatsapp.net'],
            quoted_message_id='Q-1',
            quoted_text='quoted',
            media_type='image',
            media_source='quoted',
            media_is_animated=True,
            media_caption='caption',
            media_buffer=b'media',
            message_id='MSG-1',
            push_name='Fulano',
            platform=Platform.WHATSAPP,
        )

    @pytest.mark.anyio
    async def test_reply_body_is_pinned(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = [
            BotMessage(jid='g@g.us', content=TextContent('pong')),
            BotMessage(jid='g@g.us', content=ImageBufferContent(b'\x01\x02\x03', caption='oi')),
        ]
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', json.dumps(_full_envelope()).encode())

        queue, body = broker.published[0]
        reply = json.loads(body)
        assert queue == 'replies'
        assert reply.pop('traceparent').split('-')[1] == _TRACE_ID
        assert reply == {
            'id': 'corr-1',
            'messages': [
                {'jid': 'g@g.us', 'content': {'type': 'text', 'text': 'pong'}},
                {
                    'jid': 'g@g.us',
                    'content': {
                        'type': 'image_buffer',
                        'view_once': True,
                        'caption': 'oi',
                        'buffer_b64': 'AQID',
                    },
                },
            ],
        }

    @pytest.mark.anyio
    async def test_retry_republishes_the_envelope_with_the_attempt_count(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ExternalServiceError('api down')
        await CommandConsumer(broker, handler).start()

        await broker.deliver('commands', json.dumps(_full_envelope(attempts=1)).encode())

        queue, body = broker.published[0]
        assert queue == 'commands.retry'
        assert json.loads(body) == _full_envelope(attempts=2)

    @pytest.mark.anyio
    async def test_dead_letter_is_the_envelope_as_received_then_the_error_reply(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.side_effect = ExternalServiceError('still down')
        await CommandConsumer(broker, handler).start()
        envelope = _full_envelope(attempts=CommandConsumer.MAX_ATTEMPTS - 1)

        await broker.deliver('commands', json.dumps(envelope).encode())

        (dlq_queue, dlq_body), (reply_queue, reply_body) = broker.published
        assert (dlq_queue, json.loads(dlq_body)) == ('commands.dlq', envelope)
        assert reply_queue == 'replies'
        assert json.loads(reply_body)['messages'][0]['content']['text'] == 'still down'

    @pytest.mark.anyio
    async def test_marks_the_chat_scoped_message_id_answered_after_the_reply(self, mocker):
        broker = MockBrokerPort()
        inbox = _RecordingInbox(broker)
        handler = mocker.AsyncMock()
        handler.handle.return_value = []
        await CommandConsumer(broker, handler, inbox).start()

        await broker.deliver('commands', json.dumps(_full_envelope()).encode())

        assert inbox.marked == [('g@g.us:MSG-1', ['replies'])]
