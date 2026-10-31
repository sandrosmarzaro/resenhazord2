import asyncio

import pytest
from fastapi import FastAPI

from bot.adapters.http import app
from bot.domain.commands.base import Platform
from bot.infrastructure.broker import BrokerConnectionError
from bot.infrastructure.platform_supervisor import PlatformAuthenticationError, PlatformStatus


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

    @pytest.fixture(autouse=True)
    def birthday_scheduler(self, mocker):
        scheduler = mocker.patch.object(app, 'BirthdayScheduler')
        scheduler.return_value.run = mocker.AsyncMock()
        return scheduler

    @pytest.mark.anyio
    async def test_raises_when_broker_unavailable_so_it_is_retried(self, broker, mocker):
        broker.connect.side_effect = BrokerConnectionError('down')
        agent = mocker.Mock()

        with pytest.raises(BrokerConnectionError):
            await app._connect_whatsapp(agent)

    @pytest.mark.anyio
    async def test_closes_the_half_open_broker_when_consumers_fail(self, broker, consumers, mocker):
        command_consumer, _ = consumers
        command_consumer.return_value.start.side_effect = RuntimeError('declare failed')
        agent = mocker.Mock()

        with pytest.raises(RuntimeError):
            await app._connect_whatsapp(agent)

        broker.close.assert_awaited_once_with()

    @pytest.mark.anyio
    async def test_wires_whatsapp_port_and_consumers_when_connected(
        self, mocker, broker, consumers
    ):
        command_consumer, group_consumer = consumers
        registry = mocker.MagicMock()
        mocker.patch.object(app.CommandRegistry, 'instance', return_value=registry)

        await app._connect_whatsapp(mocker.Mock())

        registry.set_whatsapp.assert_called_once()
        command_consumer.return_value.start.assert_awaited_once_with()
        group_consumer.return_value.start.assert_awaited_once_with()

    @pytest.mark.anyio
    async def test_handler_runs_the_agent_throttled_by_redis(self, mocker, broker, consumers):
        mocker.patch.object(app.settings, 'redis_url', 'redis://cache')
        from_url = mocker.patch.object(app.AgentRateLimiter, 'from_url')
        throttled = mocker.patch.object(app, 'ThrottledAgent')
        handler = mocker.patch.object(app, 'CommandHandler')
        agent = mocker.Mock()

        await app._connect_whatsapp(agent)

        from_url.assert_called_once_with('redis://cache')
        throttled.assert_called_once_with(agent, from_url.return_value)
        handler.assert_called_once_with(app.CommandRegistry.instance(), throttled.return_value)

    @pytest.mark.anyio
    async def test_agent_runs_unthrottled_without_redis(self, mocker, broker, consumers):
        mocker.patch.object(app.settings, 'redis_url', '')
        throttled = mocker.patch.object(app, 'ThrottledAgent')
        agent = mocker.Mock()

        await app._connect_whatsapp(agent)

        throttled.assert_called_once_with(agent, None)

    @pytest.mark.anyio
    async def test_consumer_skips_redeliveries_through_the_redis_inbox(
        self, mocker, broker, consumers
    ):
        command_consumer, _ = consumers
        mocker.patch.object(app.settings, 'redis_url', 'redis://cache')
        from_url = mocker.patch.object(app.RedisCommandInbox, 'from_url')
        handler = mocker.patch.object(app, 'CommandHandler')

        await app._connect_whatsapp(mocker.Mock())

        from_url.assert_called_once_with('redis://cache')
        command_consumer.assert_called_once_with(
            broker, handler.return_value, from_url.return_value
        )

    @pytest.mark.anyio
    async def test_consumer_runs_without_inbox_without_redis(self, mocker, broker, consumers):
        command_consumer, _ = consumers
        mocker.patch.object(app.settings, 'redis_url', '')
        handler = mocker.patch.object(app, 'CommandHandler')

        await app._connect_whatsapp(mocker.Mock())

        command_consumer.assert_called_once_with(broker, handler.return_value, None)

    @pytest.mark.anyio
    async def test_scheduler_claims_greetings_in_redis(
        self, mocker, broker, consumers, birthday_scheduler
    ):
        mocker.patch.object(app.settings, 'redis_url', 'redis://cache')
        from_url = mocker.patch.object(app.Redis, 'from_url')
        whatsapp = mocker.patch.object(app, 'BrokerWhatsAppClient')

        await app._connect_whatsapp(mocker.Mock())

        from_url.assert_called_with('redis://cache')
        birthday_scheduler.assert_called_once_with(whatsapp.return_value, from_url.return_value)

    @pytest.mark.anyio
    async def test_scheduler_runs_without_redis(
        self, mocker, broker, consumers, birthday_scheduler
    ):
        mocker.patch.object(app.settings, 'redis_url', '')
        whatsapp = mocker.patch.object(app, 'BrokerWhatsAppClient')

        await app._connect_whatsapp(mocker.Mock())

        birthday_scheduler.assert_called_once_with(whatsapp.return_value, None)

    @pytest.mark.anyio
    async def test_shutdown_stops_the_scheduler_and_closes_the_broker(
        self, mocker, broker, consumers, birthday_scheduler
    ):
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def run_until_cancelled():
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        birthday_scheduler.return_value.run = run_until_cancelled
        shutdown = await app._connect_whatsapp(mocker.Mock())
        await started.wait()

        await shutdown()

        assert cancelled.is_set()
        broker.close.assert_awaited_once_with()


class TestConnectTelegram:
    @pytest.mark.anyio
    async def test_starts_the_bot_and_hands_back_its_stop(self, mocker):
        mocker.patch.object(app.settings, 'telegram_token', 'token')
        mocker.patch.object(app.settings, 'telegram_bot_username', 'resenhazord_bot')
        telegram_bot = mocker.patch.object(app, 'TelegramBot')
        telegram_bot.return_value.start = mocker.AsyncMock()

        agent = mocker.Mock()

        shutdown = await app._connect_telegram(agent)

        telegram_bot.assert_called_once_with('token', 'resenhazord_bot', agent)
        telegram_bot.return_value.start.assert_awaited_once_with()
        assert shutdown == telegram_bot.return_value.stop


class TestConnectDiscord:
    @pytest.mark.anyio
    async def test_registers_commands_logs_in_and_hands_back_its_stop(self, mocker):
        mocker.patch.object(app.settings, 'discord_token', 'token')
        mocker.patch.object(app.settings, 'discord_server_guild_id', '123')
        discord_bot = mocker.patch.object(app, 'DiscordBot')
        discord_bot.return_value.start = mocker.AsyncMock()

        agent = mocker.Mock()

        shutdown = await app._connect_discord(agent)

        discord_bot.assert_called_once_with('123', agent)
        discord_bot.return_value.register_commands.assert_called_once_with()
        discord_bot.return_value.start.assert_awaited_once_with('token')
        assert shutdown == discord_bot.return_value.stop


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
            raise PlatformAuthenticationError(Platform.TELEGRAM)

        telegram_bot = mocker.patch.object(app, 'TelegramBot')
        telegram_bot.return_value.start = reject_token
        fastapi_app = FastAPI()

        async with app.lifespan(fastapi_app):
            await rejected.wait()

            assert fastapi_app.state.platforms.statuses() == {
                Platform.TELEGRAM: PlatformStatus.FAILED
            }

    @pytest.mark.anyio
    async def test_connects_whatsapp_when_rabbitmq_url_is_set(self, mocker):
        mocker.patch.object(app.settings, 'rabbitmq_url', 'amqp://broker')
        connected = asyncio.Event()
        received: list = []

        async def connect(agent):
            received.append(agent)
            connected.set()
            return mocker.AsyncMock()

        mocker.patch.object(app, '_connect_whatsapp', connect)
        fastapi_app = FastAPI()

        async with app.lifespan(fastapi_app):
            await connected.wait()

            assert fastapi_app.state.platforms.statuses() == {Platform.WHATSAPP: PlatformStatus.UP}
        assert received == [app.register_all_commands.return_value]

    @pytest.mark.anyio
    async def test_skips_whatsapp_when_rabbitmq_url_is_unset(self, mocker):
        connect = mocker.patch.object(app, '_connect_whatsapp')

        async with app.lifespan(FastAPI()):
            pass

        connect.assert_not_called()

    @pytest.mark.anyio
    async def test_starts_when_discord_rejects_the_token(self, mocker):
        mocker.patch.object(app.settings, 'discord_token', 'revoked-token')
        mocker.patch.object(app.settings, 'discord_server_guild_id', '123')
        rejected = asyncio.Event()

        async def reject_token(_token):
            rejected.set()
            raise PlatformAuthenticationError(Platform.DISCORD)

        discord_bot = mocker.patch.object(app, 'DiscordBot')
        discord_bot.return_value.start = reject_token
        fastapi_app = FastAPI()

        async with app.lifespan(fastapi_app):
            await rejected.wait()

            assert fastapi_app.state.platforms.statuses() == {
                Platform.DISCORD: PlatformStatus.FAILED
            }
