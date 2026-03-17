"""FastAPI app with WebSocket endpoint and health check."""

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from bot.adapters.http.ws_handler import WebSocketHandler
from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry

logger = structlog.get_logger()

app = FastAPI(title='Resenhazord2 Python Core')


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
