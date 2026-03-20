"""FastAPI app with WebSocket endpoint and health check."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from bot.adapters.http.ws_handler import WebSocketHandler
from bot.adapters.whatsapp.ws_client import WhatsAppWsClient
from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
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


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    logger.info('websocket_connected')

    registry = CommandRegistry.instance()
    command_handler = CommandHandler(registry)
    handler = WebSocketHandler(ws, command_handler)
    registry.set_whatsapp(WhatsAppWsClient(handler))

    app.state.ws_handler = handler

    try:
        while True:
            data = await ws.receive()
            if 'text' in data:
                await handler.handle_message(data['text'])
            elif 'bytes' in data:
                handler.receive_binary(data['bytes'])
    except WebSocketDisconnect:
        logger.info('websocket_disconnected')
        app.state.ws_handler = None
