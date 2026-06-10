import asyncio
import json

import pytest

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from bot.infrastructure.broker import RabbitBroker


class TestCommandPathOverBroker:
    @pytest.mark.anyio
    async def test_command_round_trips_to_a_published_reply(self, rabbitmq_url, mocker):
        handler = mocker.AsyncMock()
        handler.handle.return_value = [BotMessage(jid='g@g.us', content=TextContent('pong'))]

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await CommandConsumer(broker, handler).start()

        replies: list[bytes] = []
        replied = asyncio.Event()

        async def capture(body: bytes) -> None:
            replies.append(body)
            replied.set()

        await broker.consume(CommandConsumer.REPLIES_QUEUE, capture)

        envelope = {'id': 'corr-1', 'data': {'text': 'ping', 'jid': 'g@g.us', 'sender_jid': 'u@s'}}
        await broker.publish(CommandConsumer.COMMANDS_QUEUE, json.dumps(envelope).encode())

        async with asyncio.timeout(10):
            await replied.wait()
        await broker.close()

        reply = json.loads(replies[0])
        assert reply['id'] == 'corr-1'
        assert reply['messages'][0]['content']['text'] == 'pong'
