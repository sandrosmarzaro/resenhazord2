import pytest

from bot.adapters.http import app
from bot.infrastructure.broker import BrokerConnectionError


class TestStartBrokerConsumers:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_returns_none_when_broker_unavailable(self, mocker):
        broker = mocker.AsyncMock()
        broker.connect.side_effect = BrokerConnectionError('down')
        mocker.patch.object(app, 'RabbitBroker', return_value=broker)

        result = await app._start_broker_consumers()

        assert result is None

    @pytest.mark.anyio
    async def test_wires_whatsapp_port_and_consumers_when_connected(self, mocker):
        broker = mocker.AsyncMock()
        mocker.patch.object(app, 'RabbitBroker', return_value=broker)
        registry = mocker.MagicMock()
        mocker.patch.object(app.CommandRegistry, 'instance', return_value=registry)
        command_consumer = mocker.patch.object(app, 'CommandConsumer')
        command_consumer.return_value.start = mocker.AsyncMock()
        group_consumer = mocker.patch.object(app, 'GroupEventConsumer')
        group_consumer.return_value.start = mocker.AsyncMock()

        result = await app._start_broker_consumers()

        assert result is broker
        registry.set_whatsapp.assert_called_once()
        command_consumer.return_value.start.assert_awaited_once()
        group_consumer.return_value.start.assert_awaited_once()
