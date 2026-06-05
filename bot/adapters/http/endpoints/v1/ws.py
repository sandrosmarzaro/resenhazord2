"""WebSocket endpoint — bridges gateway to Python command engine."""

import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bot.adapters.http.ws_handler import WebSocketHandler
from bot.adapters.whatsapp.ws_client import WhatsAppWsClient
from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
from bot.domain.services.steal_group import StealGroupService
from bot.settings import Settings

logger = structlog.get_logger()

router = APIRouter()


@router.websocket('/ws')
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    logger.info('websocket_connected')

    registry = CommandRegistry.instance()
    command_handler = CommandHandler(registry)
    handler = WebSocketHandler(ws, command_handler)
    ws_client = WhatsAppWsClient(handler)
    registry.set_whatsapp(ws_client)

    settings = Settings()
    handler.set_steal_group_service(
        StealGroupService(ws_client, settings.resenhazord2_jid, settings.resenha_jid)
    )

    ws.app.state.ws_handler = handler
    tasks: set[asyncio.Task[None]] = set()

    def on_task_done(task: asyncio.Task[None]) -> None:
        tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            # Retrieve and log compactly: an unretrieved exception would make asyncio
            # render a rich traceback-with-locals, expensive enough at volume to peg the CPU.
            logger.warning('ws_task_failed', error=str(error), error_type=type(error).__name__)

    try:
        while True:
            data = await ws.receive()
            if 'text' in data:
                task = asyncio.create_task(handler.handle_message(data['text']))
                tasks.add(task)
                task.add_done_callback(on_task_done)
            elif 'bytes' in data:
                handler.receive_binary(data['bytes'])
    except (WebSocketDisconnect, RuntimeError):
        logger.info('websocket_disconnected')
        ws.app.state.ws_handler = None
    finally:
        for task in list(tasks):
            task.cancel()
