import asyncio

import pytest
from fastapi import FastAPI
from telegram.error import InvalidToken

from bot.adapters.http import app
from bot.adapters.telegram.bot import TelegramBot
from bot.infrastructure.broker import BrokerConnectionError
from bot.infrastructure.platform_supervisor import PlatformStatus


@pytest.fixture
def anyio_backend():
    return 'asyncio'


class TestConnectWhatsapp:
    @pytest.fixture
    def broker(self, mocker):
        broker = mocker.AsyncMock()
        mocker.patch.object(app, 'RabbitBroker', return_value=broker)
        return broker

    @pytest.fixture
    def consumers(self, mocker):
        command_consumer = mocker.patch.object(app, 'CommandConsumer')
        command_consumer.return_value.start = mocker.AsyncMock()
        group_consumer = mocker.patch.object(app, 'GroupEventConsumer')
        group_consumer.return_value.start = mocker.AsyncMock()
        return command_consumer, group_consumer

    @pytest.mark.anyio
    async def test_raises_when_broker_unavailable_so_it_is_retried(self, broker):
        broker.connect.side_effect = BrokerConnectionError('down')

        with pytest.raises(BrokerConnectionError):
            await app._connect_whatsapp()

    @pytest.mark.anyio
    async def test_closes_the_half_open_broker_when_consumers_fail(self, broker, consumers):
        command_consumer, _ = consumers
        command_consumer.return_value.start.side_effect = RuntimeError('declare failed')

        with pytest.raises(RuntimeError):
            await app._connect_whatsapp()

        broker.close.assert_awaited_once_with()

    @pytest.mark.anyio
    async def test_wires_whatsapp_port_and_consumers_when_connected(
        self, mocker, broker, consumers
    ):
        command_consumer, group_consumer = consumers
        registry = mocker.MagicMock()
        mocker.patch.object(app.CommandRegistry, 'instance', return_value=registry)

        shutdown = await app._connect_whatsapp()

        assert shutdown == broker.close
        registry.set_whatsapp.assert_called_once()
        command_consumer.return_value.start.assert_awaited_once_with()
        group_consumer.return_value.start.assert_awaited_once_with()


class TestLifespan:
    @pytest.fixture(autouse=True)
    def startup(self, mocker):
        mocker.patch.object(app, 'register_all_commands')
        mocker.patch.object(app.MongoDBConnection, 'close')
        mocker.patch.object(app.Database, 'close')
        mocker.patch.object(app.settings, 'discord_token', '')
        mocker.patch.object(app.settings, 'telegram_token', '')
        mocker.patch.object(app.settings, 'rabbitmq_url', '')

    @pytest.mark.anyio
    async def test_starts_when_telegram_rejects_the_token(self, mocker):
        mocker.patch.object(app.settings, 'telegram_token', 'revoked-token')
        rejected = asyncio.Event()

        async def reject_token():
            rejected.set()
            raise InvalidToken

        telegram_bot = mocker.patch.object(app, 'TelegramBot')
        telegram_bot.return_value.start = reject_token
        telegram_bot.is_permanent_failure = TelegramBot.is_permanent_failure
        fastapi_app = FastAPI()

        async with app.lifespan(fastapi_app):
            await rejected.wait()

            assert fastapi_app.state.platforms.statuses() == {'telegram': PlatformStatus.FAILED}

    @pytest.mark.anyio
    async def test_connects_whatsapp_when_rabbitmq_url_is_set(self, mocker):
        mocker.patch.object(app.settings, 'rabbitmq_url', 'amqp://broker')
        connected = asyncio.Event()

        async def connect():
            connected.set()
            return mocker.AsyncMock()

        mocker.patch.object(app, '_connect_whatsapp', connect)
        fastapi_app = FastAPI()

        async with app.lifespan(fastapi_app):
            await connected.wait()

            assert fastapi_app.state.platforms.statuses() == {'whatsapp': PlatformStatus.UP}

    @pytest.mark.anyio
    async def test_skips_whatsapp_when_rabbitmq_url_is_unset(self, mocker):
        connect = mocker.patch.object(app, '_connect_whatsapp')

        async with app.lifespan(FastAPI()):
            pass

        connect.assert_not_called()
