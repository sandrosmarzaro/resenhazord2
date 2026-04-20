"""FastAPI app factory — assembles routers and lifespan."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from bot.adapters.discord.bot import DiscordBot
from bot.adapters.http.endpoints.v1.health import router as health_router
from bot.adapters.http.endpoints.v1.ws import router as ws_router
from bot.adapters.telegram.bot import TelegramBot
from bot.application.register_commands import register_all_commands
from bot.infrastructure.mongodb import MongoDBConnection
from bot.settings import Settings

logger = structlog.get_logger()
settings = Settings()


def _parse_chat_ids(raw: str) -> frozenset[int]:
    return frozenset(int(part) for part in raw.split(',') if part.strip())


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    register_all_commands()
    discord_bot = None
    discord_task = None
    if settings.discord_token and settings.discord_server_guild_id:
        discord_bot = DiscordBot(settings.discord_server_guild_id)
        discord_bot.register_commands()
        discord_task = asyncio.create_task(discord_bot.client.start(settings.discord_token))
    telegram_bot = None
    if settings.telegram_token:
        telegram_bot = TelegramBot(
            settings.telegram_token,
            settings.telegram_bot_username,
            _parse_chat_ids(settings.telegram_nsfw_chat_ids),
        )
        await telegram_bot.start()
    logger.info('app_started')
    yield
    if discord_bot is not None and discord_task is not None:
        await discord_bot.client.close()
        discord_task.cancel()
    if telegram_bot is not None:
        await telegram_bot.stop()
    await MongoDBConnection.close()
    logger.info('app_stopped')


app = FastAPI(title='Resenhazord2 Python Core', lifespan=lifespan)
app.include_router(health_router)
app.include_router(ws_router)
