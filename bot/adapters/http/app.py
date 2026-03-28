"""FastAPI app factory — assembles routers and lifespan."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from bot.adapters.discord.bot import create_discord_bot
from bot.adapters.http.endpoints.v1.health import router as health_router
from bot.adapters.http.endpoints.v1.ws import router as ws_router
from bot.application.register_commands import register_all_commands
from bot.infrastructure.mongodb import MongoDBConnection
from bot.settings import Settings

logger = structlog.get_logger()
settings = Settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    register_all_commands()
    discord_client = None
    discord_task = None
    if settings.discord_token and settings.discord_guild_id:
        discord_client = create_discord_bot(settings.discord_guild_id)
        discord_task = asyncio.create_task(discord_client.start(settings.discord_token))
    logger.info('app_started')
    yield
    if discord_client is not None and discord_task is not None:
        await discord_client.close()
        discord_task.cancel()
    await MongoDBConnection.close()
    logger.info('app_stopped')


app = FastAPI(title='Resenhazord2 Python Core', lifespan=lifespan)
app.include_router(health_router)
app.include_router(ws_router)
