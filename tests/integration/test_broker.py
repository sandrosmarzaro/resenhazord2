import asyncio

import aio_pika
import pytest
from testcontainers.rabbitmq import RabbitMqContainer

from bot.infrastructure.broker import BrokerConnectionError, RabbitBroker
from bot.infrastructure.broker_topology import BrokerTopology

# What the nodes declared before the exchanges existed (ADR 0004): the topology must
# redeclare each queue with exactly these arguments, or the broker answers
# PRECONDITION_FAILED.
LEGACY_RETRY_ARGUMENTS = {
    'x-message-ttl': 30_000,
    'x-dead-letter-exchange': '',
    'x-dead-letter-routing-key': 'commands',
}
LEGACY_QUEUES = {
    'commands': None,
    'replies': None,
    'wa_actions': None,
    'wa_rpc': None,
    'group_events': None,
    'commands.dlq': None,
    'commands.retry': LEGACY_RETRY_ARGUMENTS,
}
BINDINGS = [
    ('resenhazord.commands', 'command.whatsapp', 'commands'),
    ('resenhazord.commands', 'wa.action.send_message', 'wa_actions'),
    ('resenhazord.commands', 'wa.rpc.group_metadata', 'wa_rpc'),
    ('resenhazord.events', 'reply.whatsapp', 'replies'),
    ('resenhazord.events', 'group.joined', 'group_events'),
]


class TestTopology:
    @pytest.mark.anyio
    @pytest.mark.parametrize(('exchange', 'routing_key', 'queue'), BINDINGS)
    async def test_routes_a_routing_key_to_the_queue_an_old_node_reads(
        self, rabbitmq_url, exchange, routing_key, queue
    ):
        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        async with await aio_pika.connect(rabbitmq_url) as connection:
            channel = await connection.channel()
            legacy = await channel.declare_queue(queue, durable=True)
            await legacy.purge()
            target = await channel.get_exchange(exchange)

            await target.publish(aio_pika.Message(b'roteado'), routing_key=routing_key)

            message = await legacy.get(no_ack=True, timeout=10)
        await broker.close()

        assert message.body == b'roteado'

    @pytest.mark.anyio
    async def test_redeclares_the_queues_an_old_node_declared(self):
        with RabbitMqContainer('rabbitmq:3.13') as container:
            url = _url(container)
            async with await aio_pika.connect(url) as connection:
                channel = await connection.channel()
                for name, arguments in LEGACY_QUEUES.items():
                    await channel.declare_queue(name, durable=True, arguments=arguments)

            broker = RabbitBroker()
            await broker.connect(url)

            async with await aio_pika.connect(url) as connection:
                channel = await connection.channel()
                for name, arguments in LEGACY_QUEUES.items():
                    await channel.declare_queue(name, durable=True, arguments=arguments)
            await broker.close()


def _url(container: RabbitMqContainer) -> str:
    params = container.get_connection_params()
    return f'amqp://{container.username}:{container.password}@{params.host}:{params.port}/'


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

        broker = RabbitBroker(BrokerTopology(queues={'replies_q': {}}, bindings=()))
        await broker.connect(rabbitmq_url)

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

        retry = {
            'x-message-ttl': 300,
            'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': 'retry_target',
        }
        broker = RabbitBroker(BrokerTopology(queues={'retry_target.retry': retry}, bindings=()))
        await broker.connect(rabbitmq_url)
        await broker.consume('retry_target', _record(captured, received))

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


class TestConcurrency:
    @pytest.mark.anyio
    async def test_a_slow_message_does_not_block_the_next(self, rabbitmq_url):
        release = asyncio.Event()
        fast_done = asyncio.Event()

        async def handler(body: bytes) -> None:
            if body == b'slow':
                await release.wait()
                return
            fast_done.set()

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await broker.consume('concurrency_q', handler)
        await broker.publish('concurrency_q', b'slow')
        await broker.publish('concurrency_q', b'fast')

        async with asyncio.timeout(10):
            await fast_done.wait()
        release.set()
        await broker.close()

        assert fast_done.is_set()


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


class TestDrainWithBrokerGone:
    @pytest.mark.anyio
    async def test_close_completes_when_the_broker_shut_down_underneath(self):
        async def handler(_: bytes) -> None:
            return None

        with RabbitMqContainer('rabbitmq:3.13') as container:
            broker = RabbitBroker()
            await broker.connect(_url(container))
            await broker.consume('drain_gone_q', handler)
            container.exec(['rabbitmqctl', 'stop_app'])

            async with asyncio.timeout(30):
                await broker.close()


class TestConnectFailure:
    @pytest.mark.anyio
    async def test_raises_broker_connection_error_when_unreachable(self):
        broker = RabbitBroker()

        with pytest.raises(BrokerConnectionError):
            await broker.connect('amqp://guest:guest@127.0.0.1:1/')
