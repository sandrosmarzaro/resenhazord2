import base64
import json
from typing import Any, ClassVar

import sentry_sdk
import structlog
import structlog.contextvars

from bot.adapters.http.schemas import CommandPayload
from bot.application.command_handler import CommandHandler
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Platform
from bot.domain.exceptions import BotError, DownloadError, ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.ports.broker_port import BrokerPort

logger = structlog.get_logger()


class CommandConsumer:
    COMMANDS_QUEUE = 'commands'
    REPLIES_QUEUE = 'replies'
    RETRY_QUEUE = 'commands.retry'
    DLQ_QUEUE = 'commands.dlq'
    MAX_ATTEMPTS: ClassVar[int] = 3
    DOWNLOAD_MAX_ATTEMPTS: ClassVar[int] = 1
    RETRY_TTL_MS: ClassVar[int] = 30_000

    def __init__(self, broker: BrokerPort, command_handler: CommandHandler) -> None:
        self._broker = broker
        self._command_handler = command_handler

    async def start(self) -> None:
        # Declare the publish targets up front so the publishes from inside the consume
        # callback never issue a queue-declare RPC (which would wedge the confirm). The
        # retry queue parks a failed command for a backoff then dead-letters it back to
        # commands; the DLQ is terminal (ADR 0004).
        await self._broker.declare(self.REPLIES_QUEUE)
        await self._broker.declare(self.DLQ_QUEUE)
        await self._broker.declare_retry_queue(
            self.RETRY_QUEUE, self.RETRY_TTL_MS, self.COMMANDS_QUEUE
        )
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
        # Same id on every Sentry event for this command, so one filter spans both
        # processes and the retry/DLQ hops (§12). prefetch=1 keeps it per-message.
        sentry_sdk.set_tag('correlation_id', envelope['id'])

        try:
            messages = await self._command_handler.handle(command_data)
        except ExternalServiceError as error:
            await self._retry_or_fail(envelope, command_data, error)
            return
        except BotError as error:
            await self._publish_reply(envelope, [Reply.to(command_data).text(error.user_message)])
            return
        await self._publish_reply(envelope, messages or [])

    async def _retry_or_fail(
        self, envelope: dict[str, Any], command_data: CommandData, error: ExternalServiceError
    ) -> None:
        attempts = envelope.get('attempts', 0) + 1
        if attempts < self._max_attempts(error):
            envelope['attempts'] = attempts
            await self._broker.publish(self.RETRY_QUEUE, json.dumps(envelope).encode())
            logger.warning('command_retry_scheduled', attempts=attempts, error=str(error))
            return
        logger.error('command_retries_exhausted', attempts=attempts, error=str(error))
        await self._broker.publish(self.DLQ_QUEUE, json.dumps(envelope).encode())
        await self._publish_reply(envelope, [Reply.to(command_data).text(error.user_message)])

    @classmethod
    def _max_attempts(cls, error: ExternalServiceError) -> int:
        # yt-dlp failures are usually permanent, so they skip the multi-minute ladder.
        return cls.DOWNLOAD_MAX_ATTEMPTS if isinstance(error, DownloadError) else cls.MAX_ATTEMPTS

    async def _publish_reply(self, envelope: dict[str, Any], messages: list[BotMessage]) -> None:
        reply = {
            'id': envelope['id'],
            'messages': [self._serialize(message) for message in messages],
        }
        await self._broker.publish(self.REPLIES_QUEUE, json.dumps(reply).encode())

    @staticmethod
    def _serialize(message: BotMessage) -> dict[str, Any]:
        payload = message.to_dict()
        if message.content.has_buffer:
            # Small media rides base64-inline in the reply JSON (the WS path sent it as a
            # separate binary frame); the gateway decodes it back in ReplyDeserializer.
            # has_buffer guarantees .buffer exists but the union can't be narrowed on it.
            buffer = message.content.buffer  # type: ignore[union-attr]
            payload['content']['buffer_b64'] = base64.b64encode(buffer).decode()
        return payload

    @staticmethod
    def _to_command_data(data: dict[str, Any]) -> CommandData:
        parsed = CommandPayload.model_validate(data)
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
