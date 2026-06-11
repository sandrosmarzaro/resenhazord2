import json

import pytest

from bot.adapters.broker.group_event_consumer import GroupEventConsumer
from tests.fixtures.mock_broker import MockBrokerPort


class TestGroupEventConsumer:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_dispatches_promote_event_to_steal_group(self, mocker):
        broker = MockBrokerPort()
        steal_group = mocker.AsyncMock()
        consumer = GroupEventConsumer(broker, steal_group)
        await consumer.start()

        payload = {'action': 'promote', 'id': 'g@g.us', 'participants': []}
        await broker.deliver('group_events', json.dumps(payload).encode())

        steal_group.run.assert_awaited_once_with(payload)

    @pytest.mark.anyio
    async def test_swallows_handler_error_without_propagating(self, mocker):
        broker = MockBrokerPort()
        steal_group = mocker.AsyncMock()
        steal_group.run.side_effect = RuntimeError('boom')
        consumer = GroupEventConsumer(broker, steal_group)
        await consumer.start()

        payload = {'action': 'promote', 'id': 'g@g.us', 'participants': []}
        await broker.deliver('group_events', json.dumps(payload).encode())

        steal_group.run.assert_awaited_once_with(payload)
