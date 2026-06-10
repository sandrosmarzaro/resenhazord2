"""Consumes inbound commands from the broker and publishes replies."""

import base64
import json
from typing import Any

import structlog
import structlog.contextvars

from bot.adapters.http.schemas import WSCommandData
from bot.application.command_handler import CommandHandler
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Platform
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.ports.broker_port import BrokerPort

logger = structlog.get_logger()


class CommandConsumer:
    COMMANDS_QUEUE = 'commands'
    REPLIES_QUEUE = 'replies'

    def __init__(self, broker: BrokerPort, command_handler: CommandHandler) -> None:
        self._broker = broker
        self._command_handler = command_handler

    async def start(self) -> None:
        # Declare the reply target up front so the publish from inside the consume
        # callback never issues a queue-declare RPC (which would wedge the confirm).
        await self._broker.declare(self.REPLIES_QUEUE)
        await self._broker.consume(self.COMMANDS_QUEUE, self._handle)

    async def _handle(self, body: bytes) -> None:
        envelope = json.loads(body)
        command_data = self._to_command_data(envelope['data'])

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=envelope['id'],
            jid=command_data.jid,
            sender=command_data.sender_jid,
        )

        messages = await self._run(command_data)
        reply = {'id': envelope['id'], 'messages': [message.to_dict() for message in messages]}
        await self._broker.publish(self.REPLIES_QUEUE, json.dumps(reply).encode())

    async def _run(self, command_data: CommandData) -> list[BotMessage]:
        try:
            messages = await self._command_handler.handle(command_data)
        except BotError as error:
            return [Reply.to(command_data).text(error.user_message)]
        return messages or []

    @staticmethod
    def _to_command_data(data: dict[str, Any]) -> CommandData:
        parsed = WSCommandData.model_validate(data)
        buffer = data.get('media_buffer_b64')
        return CommandData(
            text=parsed.text,
            jid=parsed.jid,
            sender_jid=parsed.sender_jid,
            participant=parsed.participant,
            is_group=parsed.is_group,
            expiration=parsed.expiration,
            mentioned_jids=parsed.mentioned_jids,
            quoted_message_id=parsed.quoted_message_id,
            quoted_text=parsed.quoted_text,
            media_type=parsed.media_type,
            media_source=parsed.media_source,
            media_is_animated=parsed.media_is_animated,
            media_caption=parsed.media_caption,
            media_buffer=base64.b64decode(buffer) if buffer else None,
            message_id=parsed.message_id,
            push_name=parsed.push_name,
            platform=Platform.WHATSAPP,
        )
