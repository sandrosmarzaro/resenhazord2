import asyncio
import json

import aio_pika
import pytest

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.infrastructure.broker import RabbitBroker
from bot.infrastructure.broker_topology import BrokerTopology
from bot.ports.broker_port import Delivery
from scripts.replay_dlq import DlqReplayer


def _dead_letter(text: str) -> aio_pika.Message:
    envelope = {
        'id': f'corr-{text}',
        'data': {'text': text, 'jid': 'g@g.us', 'sender_jid': 'u@s.whatsapp.net'},
    }
    # What a command that ran out the ladder carries: the quorum queue rejected it 4 times.
    death = {
        'queue': CommandConsumer.COMMANDS_QUEUE,
        'reason': 'rejected',
        'count': CommandConsumer.MAX_ATTEMPTS + 1,
    }
    return aio_pika.Message(json.dumps(envelope).encode(), headers={'x-death': [death]})


@pytest.fixture
async def connection(rabbitmq_url):
    async with await aio_pika.connect(rabbitmq_url) as connection:
        channel = await connection.channel()
        await BrokerTopology().declare(channel)
        for name in (CommandConsumer.DLQ_QUEUE, CommandConsumer.COMMANDS_QUEUE):
            queue = await channel.get_queue(name)
            await queue.purge()
        for text in ('ping', 'pong'):
            await channel.default_exchange.publish(
                _dead_letter(text), routing_key=CommandConsumer.DLQ_QUEUE
            )
        yield connection


async def _drain(connection, name: str) -> list[dict]:
    channel = await connection.channel()
    queue = await channel.get_queue(name)
    envelopes = []
    while message := await queue.get(no_ack=True, fail=False):
        envelopes.append(json.loads(message.body))
    return envelopes


class TestPreview:
    @pytest.mark.anyio
    async def test_lists_the_dead_letters(self, connection):
        dead_letters = await DlqReplayer(connection).preview()

        assert [envelope['data']['text'] for envelope in dead_letters] == ['ping', 'pong']

    @pytest.mark.anyio
    async def test_keeps_the_dead_letters_queued(self, connection):
        await DlqReplayer(connection).preview()

        assert len(await _drain(connection, CommandConsumer.DLQ_QUEUE)) == 2


class TestReplay:
    @pytest.mark.anyio
    async def test_moves_dead_letters_back_to_the_commands_queue(self, connection):
        replayed = await DlqReplayer(connection).replay()

        commands = await _drain(connection, CommandConsumer.COMMANDS_QUEUE)
        assert replayed == 2
        assert [envelope['data']['text'] for envelope in commands] == ['ping', 'pong']
        assert await _drain(connection, CommandConsumer.DLQ_QUEUE) == []

    @pytest.mark.anyio
    async def test_replayed_commands_restart_the_retry_ladder(self, connection, rabbitmq_url):
        both = asyncio.Event()
        runs: list[tuple[int, bool]] = []

        async def record(delivery: Delivery) -> None:
            runs.append((delivery.attempt, json.loads(delivery.body)['replayed']))
            if len(runs) == len(('ping', 'pong')):
                both.set()

        broker = RabbitBroker()
        await broker.connect(rabbitmq_url)
        await DlqReplayer(connection).replay()

        await broker.consume(CommandConsumer.COMMANDS_QUEUE, record)
        async with asyncio.timeout(10):
            await both.wait()
        await broker.close()

        assert runs == [(1, True), (1, True)]
