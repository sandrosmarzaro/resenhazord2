import asyncio
import json
import time
from contextlib import AsyncExitStack
from functools import partial
from typing import Any, ClassVar

import sentry_sdk
import structlog
import structlog.contextvars
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from bot.adapters.broker.command_envelope import CommandEnvelope
from bot.adapters.broker.delivery_guard import DeliveryGuard
from bot.adapters.broker.retry_router import RetryRouter
from bot.application.command_handler import CommandHandler
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command
from bot.domain.exceptions import BotError, ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.metrics import record_lane_wait, track_in_flight
from bot.infrastructure.trace_propagation import extract_trace_context, inject_trace_context
from bot.ports.broker_port import BrokerPort
from bot.ports.command_inbox_port import CommandInboxPort

logger = structlog.get_logger()
_tracer = trace.get_tracer(__name__)


class CommandConsumer:
    COMMANDS_QUEUE = 'commands'
    REPLIES_QUEUE = 'replies'
    RETRY_QUEUE = 'commands.retry'
    DLQ_QUEUE = 'commands.dlq'
    MAX_ATTEMPTS: ClassVar[int] = RetryRouter.MAX_ATTEMPTS
    DOWNLOAD_MAX_ATTEMPTS: ClassVar[int] = RetryRouter.DOWNLOAD_MAX_ATTEMPTS
    RETRY_TTL_MS: ClassVar[int] = 30_000
    MS_PER_SECOND: ClassVar[int] = 1000
    UNEXPECTED_ERROR_MESSAGE: ClassVar[str] = 'Ocorreu um erro ao executar o comando.'

    def __init__(
        self,
        broker: BrokerPort,
        command_handler: CommandHandler,
        inbox: CommandInboxPort | None = None,
    ) -> None:
        self._broker = broker
        self._command_handler = command_handler
        self._delivery = DeliveryGuard(inbox)
        self._retries = RetryRouter(broker, self.RETRY_QUEUE, self.DLQ_QUEUE)
        self._exclusive_lane = asyncio.Lock()

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
        # A fresh Sentry isolation scope per message: set_tag mutates the scope object,
        # which the consume tasks share by reference, so the last command's tags used to
        # stamp later, unrelated events (e.g. the deploy shutdown error).
        track_in_flight(1)
        try:
            with sentry_sdk.isolation_scope():
                # The lane, once entered, is held until the reply is published:
                # serializing a media reply is the memory peak, not running the command.
                async with AsyncExitStack() as lane:
                    await self._process(json.loads(body), lane)
        finally:
            track_in_flight(-1)

    async def _process(self, envelope: dict[str, Any], lane: AsyncExitStack) -> None:
        command_data = CommandEnvelope.to_command_data(envelope['data'])

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=envelope['id'],
            jid=command_data.jid,
            sender=command_data.sender_jid,
        )
        # Same id on every Sentry event for this command, so one filter spans both
        # processes and the retry/DLQ hops (§12). Each delivery runs in its own task,
        # under its own isolation scope, so concurrent commands keep their own tags.
        sentry_sdk.set_tag('correlation_id', envelope['id'])

        with self._delivery.claim(envelope) as claimed:
            if not claimed:
                logger.info('command_duplicate_skipped')
                return
            await self._answer(envelope, command_data, lane)

    async def _answer(
        self, envelope: dict[str, Any], command_data: CommandData, lane: AsyncExitStack
    ) -> None:
        if await self._delivery.already_answered(envelope):
            logger.info('command_redelivery_skipped')
            return

        # Continue the trace the edge started: the parent context rides in the
        # envelope (not AMQP headers), so the whole command — and any span it
        # spawns — hangs under the originating gateway span.
        parent = extract_trace_context(envelope)
        outcome = 'success'
        # RED (rate/errors/duration) is derived from this span by the spanmetrics
        # connector in the core Alloy collector, split by the command.outcome
        # attribute — so no manual count/latency here.
        with _tracer.start_as_current_span('command.handle', context=parent) as span:
            try:
                messages = await self._command_handler.handle(
                    command_data, on_match=partial(self._enter_lane, lane)
                )
            except ExternalServiceError as error:
                outcome = 'external_error'
                span.set_status(StatusCode.ERROR, type(error).__name__)
                await self._retry_or_fail(envelope, command_data, error)
            except BotError as error:
                outcome = 'bot_error'
                await self._publish_reply(
                    envelope, [Reply.to(command_data).text(error.user_message)]
                )
            # Anything else escaped the consume callback: aio_pika rejected the message
            # without requeue, the user got no reply, and the span still said success.
            except Exception as error:
                outcome = 'unexpected_error'
                # Only the type: an httpx message carries the URL, query secrets and all
                # (the Telegram token leak, PR #204). Sentry gets the full exception.
                span.set_status(StatusCode.ERROR, type(error).__name__)
                logger.exception('command_unexpected_error')
                await self._publish_reply(
                    envelope, [Reply.to(command_data).text(self.UNEXPECTED_ERROR_MESSAGE)]
                )
            else:
                await self._publish_reply(envelope, messages or [])
            finally:
                span.set_attribute('command.outcome', outcome)

    async def _enter_lane(self, lane: AsyncExitStack, command: Command) -> None:
        if not command.config.exclusive:
            return
        queued_at = time.monotonic()
        await lane.enter_async_context(self._exclusive_lane)
        record_lane_wait((time.monotonic() - queued_at) * self.MS_PER_SECOND)

    async def _retry_or_fail(
        self, envelope: dict[str, Any], command_data: CommandData, error: ExternalServiceError
    ) -> None:
        if await self._retries.route(envelope, error):
            await self._publish_reply(envelope, [Reply.to(command_data).text(error.user_message)])

    async def _publish_reply(self, envelope: dict[str, Any], messages: list[BotMessage]) -> None:
        reply = CommandEnvelope.reply(envelope['id'], messages)
        # Carry the trace forward so the gateway's reply consumer can join it (Phase 4).
        inject_trace_context(reply)
        await self._broker.publish(self.REPLIES_QUEUE, json.dumps(reply).encode())
        # Marked only once the final reply is out: a crash before this line lets the
        # redelivery run again, and a scheduled retry never reaches here.
        await self._delivery.mark_answered(envelope)
