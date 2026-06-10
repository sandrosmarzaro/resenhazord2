"""RabbitMQ broker adapter (aio-pika) implementing BrokerPort."""

import aio_pika
import structlog

from bot.ports.broker_port import MessageHandler

logger = structlog.get_logger()


class BrokerConnectionError(Exception):
    pass


class RabbitBroker:
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
        except (OSError, aio_pika.exceptions.AMQPError) as error:
            raise BrokerConnectionError(str(error)) from error

    async def declare(self, queue: str) -> None:
        # Declare topology once at startup, never on the publish hot path: a
        # Queue.Declare RPC issued from inside a consume callback wedges the channel's
        # next publisher-confirm. Publishing assumes the queue already exists.
        channel = self._active(self._publish_channel)
        await channel.declare_queue(queue, durable=True)

    async def publish(self, queue: str, body: bytes) -> None:
        channel = self._active(self._publish_channel)
        message = aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        exchange = channel.default_exchange
        await exchange.publish(message, routing_key=queue)

    async def consume(self, queue: str, handler: MessageHandler) -> None:
        channel = self._active(self._consume_channel)
        declared = await channel.declare_queue(queue, durable=True)
        await declared.consume(self._make_callback(handler))

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
