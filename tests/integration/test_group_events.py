import asyncio
import json

import pytest

from bot.adapters.broker.group_event_consumer import GroupEventConsumer
from bot.infrastructure.broker import RabbitBroker


class TestGroupEventsOverBroker:
    @pytest.mark.anyio
    async def test_consumer_dispatches_published_event(self, rabbitmq_url, mocker):
        dispatched = asyncio.Event()
        steal_group = mocker.AsyncMock()
        steal_group.run.side_effect = lambda *_: dispatched.set()

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await GroupEventConsumer(broker, steal_group).start()

        payload = {'action': 'promote', 'id': 'g@g.us', 'participants': []}
        await broker.publish(GroupEventConsumer.QUEUE, json.dumps(payload).encode())

        async with asyncio.timeout(10):
            await dispatched.wait()
        await broker.close()

        steal_group.run.assert_awaited_once_with(payload)
