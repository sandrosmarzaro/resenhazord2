"""RabbitMQ broker adapter (aio-pika) implementing BrokerPort."""

import aio_pika
import structlog

from bot.ports.broker_port import MessageHandler

logger = structlog.get_logger()


class BrokerConnectionError(Exception):
    pass


class RabbitBroker:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self, url: str) -> None:
        try:
            self._connection = await aio_pika.connect_robust(url)
            self._channel = await self._connection.channel(publisher_confirms=True)
        except (OSError, aio_pika.exceptions.AMQPError) as error:
            raise BrokerConnectionError(str(error)) from error

    async def publish(self, queue: str, body: bytes) -> None:
        channel = self._active_channel()
        await channel.declare_queue(queue, durable=True)
        message = aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        exchange = channel.default_exchange
        await exchange.publish(message, routing_key=queue)

    async def consume(self, queue: str, handler: MessageHandler) -> None:
        channel = self._active_channel()
        declared = await channel.declare_queue(queue, durable=True)
        await declared.consume(self._make_callback(handler))

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None

    def _active_channel(self) -> aio_pika.abc.AbstractChannel:
        if self._channel is None:
            message = 'Broker channel not connected; call connect() first'
            raise RuntimeError(message)
        return self._channel

    @staticmethod
    def _make_callback(handler: MessageHandler):
        async def on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                await handler(message.body)

        return on_message
