import asyncio

import pytest
from testcontainers.rabbitmq import RabbitMqContainer

from bot.infrastructure.broker import RabbitBroker


class TestRoundTrip:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.fixture(scope='class')
    def broker_url(self):
        with RabbitMqContainer('rabbitmq:3.13') as container:
            params = container.get_connection_params()
            yield (f'amqp://{container.username}:{container.password}@{params.host}:{params.port}/')

    @pytest.mark.anyio
    async def test_publishes_and_consumes_a_message(self, broker_url):
        received = asyncio.Event()
        captured: list[bytes] = []

        async def handler(body: bytes) -> None:
            captured.append(body)
            received.set()

        broker = RabbitBroker()
        await broker.connect(broker_url)
        await broker.consume('round_trip', handler)

        await broker.publish('round_trip', b'ola mundo')

        async with asyncio.timeout(10):
            await received.wait()
        await broker.close()

        assert captured == [b'ola mundo']
