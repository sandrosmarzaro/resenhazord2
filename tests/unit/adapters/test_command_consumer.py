import base64
import json

import pytest

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.domain.exceptions import BotError
from bot.domain.models.contents.image_content import ImageBufferContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from tests.fixtures.mock_broker import MockBrokerPort


def _envelope(text: str, jid: str = 'g@g.us') -> bytes:
    payload = {
        'id': 'corr-1',
        'data': {'text': text, 'jid': jid, 'sender_jid': 'u@s.whatsapp.net'},
    }
    return json.dumps(payload).encode()


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
