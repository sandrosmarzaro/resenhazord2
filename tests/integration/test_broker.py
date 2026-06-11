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


class TestPublishInsideConsume:
    @pytest.mark.anyio
    async def test_confirmed_publish_from_inside_a_consume_callback(self, rabbitmq_url):
        received = asyncio.Event()
        captured: list[bytes] = []

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await broker.declare('replies_q')

        async def relay(_: bytes) -> None:
            await broker.publish('replies_q', b'reply')

        async def collect(body: bytes) -> None:
            captured.append(body)
            received.set()

        await broker.consume('commands_q', relay)
        await broker.consume('replies_q', collect)

        await broker.publish('commands_q', b'command')

        async with asyncio.timeout(10):
            await received.wait()
        await broker.close()

        assert captured == [b'reply']


class TestRpc:
    @pytest.mark.anyio
    async def test_rpc_call_round_trips_through_a_responder(self, rabbitmq_url):
        import json

        responder = RabbitBroker()
        await responder.connect(rabbitmq_url)

        async def handle(body: bytes) -> bytes:
            request = json.loads(body)
            return json.dumps({'echo': request['jids']}).encode()

        await responder.rpc_respond('wa_rpc', handle)

        client = RabbitBroker()
        await client.connect(rabbitmq_url)

        async with asyncio.timeout(10):
            reply = await client.rpc_call('wa_rpc', json.dumps({'jids': ['x@s']}).encode())

        await client.close()
        await responder.close()

        assert json.loads(reply) == {'echo': ['x@s']}


class TestRetryQueue:
    @pytest.mark.anyio
    async def test_message_dead_letters_back_to_the_target_after_ttl(self, rabbitmq_url):
        received = asyncio.Event()
        captured: list[bytes] = []

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await broker.consume('retry_target', _record(captured, received))
        await broker.declare_retry_queue(
            'retry_target.retry', ttl_ms=300, dead_letter_to='retry_target'
        )

        await broker.publish('retry_target.retry', b'delayed')

        async with asyncio.timeout(10):
            await received.wait()
        await broker.close()

        assert captured == [b'delayed']


def _record(captured: list[bytes], event: asyncio.Event):
    async def handler(body: bytes) -> None:
        captured.append(body)
        event.set()

    return handler


class TestGracefulDrain:
    @pytest.mark.anyio
    async def test_close_waits_for_the_in_flight_message(self, rabbitmq_url):
        started = asyncio.Event()
        release = asyncio.Event()
        finished: list[bytes] = []

        async def slow_handler(body: bytes) -> None:
            started.set()
            await release.wait()
            finished.append(body)

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await broker.consume('drain_q', slow_handler)
        await broker.publish('drain_q', b'work')

        async with asyncio.timeout(10):
            await started.wait()

        close_task = asyncio.create_task(broker.close())
        release.set()
        async with asyncio.timeout(10):
            await close_task

        assert finished == [b'work']


class TestConnectFailure:
    @pytest.mark.anyio
    async def test_raises_broker_connection_error_when_unreachable(self):
        broker = RabbitBroker()

        with pytest.raises(BrokerConnectionError):
            await broker.connect('amqp://guest:guest@127.0.0.1:1/')
