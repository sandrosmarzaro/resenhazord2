"""RabbitMQ broker adapter (aio-pika) implementing BrokerPort."""

import asyncio
import uuid

import aio_pika
import structlog

from bot.ports.broker_port import MessageHandler, RpcHandler

logger = structlog.get_logger()


class BrokerConnectionError(Exception):
    pass


class RabbitBroker:
    PREFETCH_COUNT = 1

    def __init__(self) -> None:
        self._publish_connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._consume_connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._publish_channel: aio_pika.abc.AbstractChannel | None = None
        self._consume_channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self, url: str) -> None:
        try:
            # Separate connections for publishing and consuming: a confirm-mode publish
            # issued from inside a consume callback never receives its ack on a shared
            # connection (consumer back-pressure stalls the publisher's reader loop).
            self._publish_connection = await aio_pika.connect_robust(url)
            self._consume_connection = await aio_pika.connect_robust(url)
            self._publish_channel = await self._publish_connection.channel(publisher_confirms=True)
            self._consume_channel = await self._consume_connection.channel()
            # One unacked message at a time, so a slow command can't starve others and a
            # second worker round-robins with no code change (PRD §5).
            await self._consume_channel.set_qos(prefetch_count=self.PREFETCH_COUNT)
        except (OSError, aio_pika.exceptions.AMQPError) as error:
            raise BrokerConnectionError(str(error)) from error

    async def declare(self, queue: str) -> None:
        # Declare topology once at startup, never on the publish hot path: a
        # Queue.Declare RPC issued from inside a consume callback wedges the channel's
        # next publisher-confirm. Publishing assumes the queue already exists.
        channel = self._active(self._publish_channel)
        await channel.declare_queue(queue, durable=True)

    async def declare_retry_queue(self, queue: str, ttl_ms: int, dead_letter_to: str) -> None:
        # A message parked here waits ttl_ms, then dead-letters (default exchange) to
        # dead_letter_to — the backoff hop of the retry ladder (ADR 0004).
        channel = self._active(self._publish_channel)
        await channel.declare_queue(
            queue,
            durable=True,
            arguments={
                'x-message-ttl': ttl_ms,
                'x-dead-letter-exchange': '',
                'x-dead-letter-routing-key': dead_letter_to,
            },
        )

    async def publish(self, queue: str, body: bytes) -> None:
        channel = self._active(self._publish_channel)
        message = aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        exchange = channel.default_exchange
        await exchange.publish(message, routing_key=queue)

    async def consume(self, queue: str, handler: MessageHandler) -> None:
        channel = self._active(self._consume_channel)
        declared = await channel.declare_queue(queue, durable=True)
        await declared.consume(self._make_callback(handler))

    async def rpc_call(self, queue: str, body: bytes) -> bytes:
        # The caller owns the deadline via `asyncio.timeout(...)`; on cancellation the
        # finally still tears down the temporary callback queue's consumer.
        callback_queue = await self._active(self._consume_channel).declare_queue(exclusive=True)
        correlation_id = str(uuid.uuid4())
        future: asyncio.Future[bytes] = asyncio.get_event_loop().create_future()
        consumer_tag = await callback_queue.consume(self._rpc_response(correlation_id, future))
        request = aio_pika.Message(
            body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=correlation_id,
            reply_to=callback_queue.name,
        )
        await self._active(self._publish_channel).default_exchange.publish(
            request, routing_key=queue
        )
        try:
            return await future
        finally:
            await callback_queue.cancel(consumer_tag)

    async def rpc_respond(self, queue: str, handler: RpcHandler) -> None:
        declared = await self._active(self._consume_channel).declare_queue(queue, durable=True)
        await declared.consume(self._make_rpc_callback(handler))

    async def close(self) -> None:
        for connection in (self._publish_connection, self._consume_connection):
            if connection:
                await connection.close()
        self._publish_connection = None
        self._consume_connection = None
        self._publish_channel = None
        self._consume_channel = None

    @staticmethod
    def _active(channel: aio_pika.abc.AbstractChannel | None) -> aio_pika.abc.AbstractChannel:
        if channel is None:
            message = 'Broker channel not connected; call connect() first'
            raise RuntimeError(message)
        return channel

    @staticmethod
    def _make_callback(handler: MessageHandler):
        async def on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                await handler(message.body)

        return on_message

    @staticmethod
    def _rpc_response(correlation_id: str, future: asyncio.Future[bytes]):
        async def on_response(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                if message.correlation_id == correlation_id and not future.done():
                    future.set_result(message.body)

        return on_response

    def _make_rpc_callback(self, handler: RpcHandler):
        async def on_request(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                if message.reply_to is None:
                    return
                result = await handler(message.body)
                reply = aio_pika.Message(result, correlation_id=message.correlation_id)
                await self._active(self._publish_channel).default_exchange.publish(
                    reply, routing_key=message.reply_to
                )

        return on_request
