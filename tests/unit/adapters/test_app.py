import asyncio

import pytest
from fastapi import FastAPI
from telegram.error import InvalidToken

from bot.adapters.http import app
from bot.adapters.telegram.bot import TelegramBot
from bot.infrastructure.broker import BrokerConnectionError
from bot.infrastructure.platform_supervisor import PlatformStatus


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


class TestLifespan:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.fixture
    def startup(self, mocker):
        mocker.patch.object(app, 'register_all_commands')
        mocker.patch.object(app, '_start_broker_consumers', return_value=None)
        mocker.patch.object(app.MongoDBConnection, 'close')
        mocker.patch.object(app.Database, 'close')
        mocker.patch.object(app.settings, 'discord_token', '')
        mocker.patch.object(app.settings, 'telegram_token', 'revoked-token')

    @pytest.mark.anyio
    async def test_starts_when_telegram_rejects_the_token(self, mocker, startup):
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
