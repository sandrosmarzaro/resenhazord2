"""FastAPI app factory — assembles routers and lifespan."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.adapters.broker.group_event_consumer import GroupEventConsumer
from bot.adapters.discord.bot import DiscordBot
from bot.adapters.http.endpoints.v1.health import router as health_router
from bot.adapters.http.endpoints.v1.platforms import router as platforms_router
from bot.adapters.telegram.bot import TelegramBot
from bot.adapters.whatsapp.broker_client import BrokerWhatsAppClient
from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
from bot.application.register_commands import register_all_commands
from bot.domain.commands.base import Platform
from bot.domain.services.steal_group import StealGroupService
from bot.infrastructure.broker import RabbitBroker
from bot.infrastructure.database import Database
from bot.infrastructure.mongodb import MongoDBConnection
from bot.infrastructure.platform_supervisor import PlatformSupervisor, Shutdown
from bot.settings import Settings

logger = structlog.get_logger()
settings = Settings()


def _parse_chat_ids(raw: str) -> frozenset[int]:
    return frozenset(int(part) for part in raw.split(',') if part.strip())


async def _connect_whatsapp() -> Shutdown:
    broker = RabbitBroker()
    try:
        await broker.connect(settings.rabbitmq_url)
        whatsapp = BrokerWhatsAppClient(broker)
        registry = CommandRegistry.instance()
        registry.set_whatsapp(whatsapp)
        await CommandConsumer(broker, CommandHandler(registry)).start()
        steal_group = StealGroupService(whatsapp, settings.resenhazord2_jid, settings.resenha_jid)
        await GroupEventConsumer(broker, steal_group).start()
    except BaseException:
        # Close the half-open connections before the supervisor retries with a fresh broker.
        await broker.close()
        raise
    return broker.close


async def _connect_telegram() -> Shutdown:
    # A fresh bot per attempt: a half-initialized one would re-register its handlers.
    telegram_bot = TelegramBot(
        settings.telegram_token,
        settings.telegram_bot_username,
        _parse_chat_ids(settings.telegram_nsfw_chat_ids),
    )
    await telegram_bot.start()
    return telegram_bot.stop


async def _connect_discord() -> Shutdown:
    discord_bot = DiscordBot(settings.discord_server_guild_id)
    discord_bot.register_commands()
    await discord_bot.start(settings.discord_token)
    return discord_bot.stop


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    register_all_commands()
    platforms = PlatformSupervisor()
    fastapi_app.state.platforms = platforms
    if settings.rabbitmq_url:
        # Broker outages heal on their own, so WhatsApp never gives up retrying.
        platforms.start(Platform.WHATSAPP, _connect_whatsapp)
    if settings.discord_token and settings.discord_server_guild_id:
        platforms.start(Platform.DISCORD, _connect_discord)
    if settings.telegram_token:
        platforms.start(Platform.TELEGRAM, _connect_telegram)
    logger.info('app_started')
    yield
    await platforms.stop()
    await MongoDBConnection.close()
    await Database.close()
    logger.info('app_stopped')


app = FastAPI(title='Resenhazord2 Python Core', lifespan=lifespan)
app.include_router(health_router)
app.include_router(platforms_router)
