"""FastAPI app factory — assembles routers and lifespan."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from bot.adapters.http.endpoints.v1.health import router as health_router
from bot.adapters.http.endpoints.v1.ws import router as ws_router
from bot.application.register_commands import register_all_commands
from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    register_all_commands()
    logger.info('app_started')
    yield
    await MongoDBConnection.close()
    logger.info('app_stopped')


app = FastAPI(title='Resenhazord2 Python Core', lifespan=lifespan)
app.include_router(health_router)
app.include_router(ws_router)
