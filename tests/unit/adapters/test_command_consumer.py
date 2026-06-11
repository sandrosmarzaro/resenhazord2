import base64
import json

import pytest

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.domain.exceptions import BotError, DownloadError, ExternalServiceError, ValidationError
from bot.domain.models.contents.image_content import ImageBufferContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from tests.fixtures.mock_broker import MockBrokerPort


def _envelope(text: str, jid: str = 'g@g.us', attempts: int | None = None) -> bytes:
    payload: dict = {
        'id': 'corr-1',
        'data': {'text': text, 'jid': jid, 'sender_jid': 'u@s.whatsapp.net'},
    }
    if attempts is not None:
        payload['attempts'] = attempts
    return json.dumps(payload).encode()


def _queues(broker: MockBrokerPort) -> list[str]:
    return [queue for queue, _ in broker.published]


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
    async def test_no_match_publishes_empty_terminal_reply(self, mocker):
        broker = MockBrokerPort()
        handler = mocker.AsyncMock()
        handler.handle.return_value = None
        consumer = CommandConsumer(broker, handler)
        await consumer.start()

        await broker.deliver('commands', _envelope('ping'))

        _, body = broker.published[0]
        assert json.loads(body) == {'id': 'corr-1', 'messages': []}
