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
        consumer = GroupEventConsumer(broker, steal_group, mocker.AsyncMock())
        await consumer.start()

        payload = {'action': 'promote', 'id': 'g@g.us', 'participants': []}
        await broker.deliver('group_events', json.dumps(payload).encode())

        steal_group.run.assert_awaited_once_with(payload)

    @pytest.mark.anyio
    async def test_dispatches_joined_event_to_group_welcome(self, mocker):
        broker = MockBrokerPort()
        group_welcome = mocker.AsyncMock()
        consumer = GroupEventConsumer(broker, mocker.AsyncMock(), group_welcome)
        await consumer.start()

        payload = {'action': 'joined', 'id': 'g@g.us'}
        await broker.deliver('group_events', json.dumps(payload).encode())

        group_welcome.run.assert_awaited_once_with(payload)

    @pytest.mark.anyio
    async def test_ignores_unhandled_action(self, mocker):
        broker = MockBrokerPort()
        steal_group = mocker.AsyncMock()
        group_welcome = mocker.AsyncMock()
        consumer = GroupEventConsumer(broker, steal_group, group_welcome)
        await consumer.start()

        payload = {'action': 'remove', 'id': 'g@g.us', 'participants': []}
        await broker.deliver('group_events', json.dumps(payload).encode())

        steal_group.run.assert_not_awaited()
        group_welcome.run.assert_not_awaited()

    @pytest.mark.anyio
    async def test_swallows_handler_error_without_propagating(self, mocker):
        broker = MockBrokerPort()
        steal_group = mocker.AsyncMock()
        steal_group.run.side_effect = RuntimeError('boom')
        consumer = GroupEventConsumer(broker, steal_group, mocker.AsyncMock())
        await consumer.start()

        payload = {'action': 'promote', 'id': 'g@g.us', 'participants': []}
        await broker.deliver('group_events', json.dumps(payload).encode())

        steal_group.run.assert_awaited_once_with(payload)
