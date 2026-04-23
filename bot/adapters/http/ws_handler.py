"""WebSocket message router — dispatches command requests and wa_result callbacks."""

import asyncio
import uuid
from typing import Any

import structlog
import structlog.contextvars
from starlette.websockets import WebSocket

from bot.adapters.http.schemas import WSCommandData, WSMessage
from bot.application.command_handler import CommandHandler
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Platform
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.steal_group import StealGroupService

logger = structlog.get_logger()


class WebSocketHandler:
    def __init__(self, ws: WebSocket, command_handler: CommandHandler) -> None:
        self._ws = ws
        self._command_handler = command_handler
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._pending_binary: bytes | None = None
        self._steal_group: StealGroupService | None = None

    def set_steal_group_service(self, service: StealGroupService) -> None:
        self._steal_group = service

    async def handle_message(self, raw: str) -> None:
        msg = WSMessage.model_validate_json(raw)

        if msg.type == 'command':
            await self._handle_command(msg)
        elif msg.type == 'group_event':
            await self._handle_group_event(msg)
        elif msg.type == 'wa_result':
            self._resolve_pending(msg)
        elif msg.type == 'error':
            self._reject_pending(msg)
        else:
            logger.warning('unknown_message_type', type=msg.type, id=msg.id)

    def receive_binary(self, data: bytes) -> None:
        self._pending_binary = data

    def take_binary(self) -> bytes | None:
        data = self._pending_binary
        self._pending_binary = None
        return data

    async def _handle_command(self, msg: WSMessage) -> None:
        if msg.data is None:
            await self._send_error(msg.id, 'Missing data in command message')
            return

        cmd_data = WSCommandData.model_validate(msg.data)
        logger.info(
            "ws_command_received",
            text=cmd_data.text,
            mentioned_jids=cmd_data.mentioned_jids,
            is_group=cmd_data.is_group,
        )
        media_buffer = self.take_binary() if cmd_data.media_buffer_size > 0 else None
        command_data = CommandData(
            text=cmd_data.text,
            jid=cmd_data.jid,
            sender_jid=cmd_data.sender_jid,
            participant=cmd_data.participant,
            is_group=cmd_data.is_group,
            expiration=cmd_data.expiration,
            mentioned_jids=cmd_data.mentioned_jids,
            quoted_message_id=cmd_data.quoted_message_id,
            quoted_text=cmd_data.quoted_text,
            media_type=cmd_data.media_type,
            media_source=cmd_data.media_source,
            media_is_animated=cmd_data.media_is_animated,
            media_caption=cmd_data.media_caption,
            media_buffer=media_buffer,
            message_id=cmd_data.message_id,
            push_name=cmd_data.push_name,
            platform=Platform.WHATSAPP,
        )

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            jid=command_data.jid,
            sender=command_data.sender_jid,
            msg_id=msg.id,
        )

        async def send_ack() -> None:
            await self._ws.send_json({'id': msg.id, 'type': 'command_ack'})

        try:
            messages = await self._command_handler.handle(command_data, on_match=send_ack)
        except BotError as e:
            messages = [Reply.to(command_data).text(e.user_message)]
        except Exception as e:
            logger.exception('command_handler_error', id=msg.id)
            await self._send_error(msg.id, str(e), 'EXECUTION_ERROR')
            return

        if messages is None:
            await self._ws.send_json({'id': msg.id, 'type': 'no_match'})
            return

        await self._send_command_response(msg.id, messages)

    async def _handle_group_event(self, msg: WSMessage) -> None:
        if not self._steal_group or msg.data is None:
            return
        try:
            await self._steal_group.run(msg.data)
        except Exception:
            logger.exception('group_event_error', id=msg.id)

    async def _send_command_response(self, msg_id: str, messages: list[BotMessage]) -> None:
        # Prefix each binary frame with "<msg_id>:" so the TS side can route it
        # to the correct pending request when multiple commands run concurrently.
        id_prefix = msg_id.encode() + b':'
        for m in messages:
            if m.content.has_buffer:
                await self._ws.send_bytes(id_prefix + m.content.buffer)  # type: ignore[union-attr]
        await self._ws.send_json(
            {
                'id': msg_id,
                'type': 'command_response',
                'data': {'messages': [m.to_dict() for m in messages]},
            }
        )

    async def _send_error(self, msg_id: str, message: str, code: str = 'UNKNOWN_ERROR') -> None:
        await self._ws.send_json(
            {
                'id': msg_id,
                'type': 'error',
                'data': {'message': message, 'code': code},
            }
        )

    def _resolve_pending(self, msg: WSMessage) -> None:
        future = self._pending.pop(msg.id, None)
        if future and not future.done():
            future.set_result(msg.data or {})
        elif future is None:
            logger.warning('no_pending_future', id=msg.id)

    def _reject_pending(self, msg: WSMessage) -> None:
        future = self._pending.pop(msg.id, None)
        if future and not future.done():
            error_msg = (msg.data or {}).get('message', 'Unknown wa_call error')
            future.set_exception(RuntimeError(error_msg))
        elif future is None:
            logger.warning('wa_call_error_no_pending', id=msg.id, data=msg.data)

    async def call_whatsapp(
        self, method: str, data: dict[str, Any], *, deadline: float = 30.0
    ) -> dict[str, Any]:
        """Send wa_call to TS side and await wa_result."""
        msg_id = str(uuid.uuid4())
        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future
        await self._ws.send_json(
            {
                'id': msg_id,
                'type': 'wa_call',
                'method': method,
                'data': data,
            }
        )
        return await asyncio.wait_for(future, timeout=deadline)
