"""WebSocket endpoint — bridges gateway to Python command engine."""

import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bot.adapters.broker.group_event_consumer import GroupEventConsumer
from bot.adapters.http.ws_handler import WebSocketHandler
from bot.adapters.whatsapp.ws_client import WhatsAppWsClient
from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
from bot.domain.services.steal_group import StealGroupService
from bot.infrastructure.broker import BrokerConnectionError, RabbitBroker
from bot.settings import Settings

logger = structlog.get_logger()

router = APIRouter()


async def _start_group_events(steal_group: StealGroupService, url: str) -> RabbitBroker | None:
    broker = RabbitBroker()
    try:
        await broker.connect(url)
        await GroupEventConsumer(broker, steal_group).start()
    except BrokerConnectionError:
        logger.warning('group_events_broker_unavailable')
        return None
    return broker


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
    steal_group = StealGroupService(ws_client, settings.resenhazord2_jid, settings.resenha_jid)
    handler.set_steal_group_service(steal_group)
    broker = await _start_group_events(steal_group, settings.rabbitmq_url)

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
        if broker is not None:
            await broker.close()
