import asyncio

import pytest

from bot.infrastructure.broker import BrokerConnectionError, RabbitBroker


class TestRoundTrip:
    @pytest.mark.anyio
    async def test_publishes_and_consumes_a_message(self, rabbitmq_url):
        received = asyncio.Event()
        captured: list[bytes] = []

        async def handler(body: bytes) -> None:
            captured.append(body)
            received.set()

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await broker.consume('round_trip', handler)

        await broker.publish('round_trip', b'ola mundo')

        async with asyncio.timeout(10):
            await received.wait()
        await broker.close()

        assert captured == [b'ola mundo']


class TestConnectFailure:
    @pytest.mark.anyio
    async def test_raises_broker_connection_error_when_unreachable(self):
        broker = RabbitBroker()

        with pytest.raises(BrokerConnectionError):
            await broker.connect('amqp://guest:guest@127.0.0.1:1/')
