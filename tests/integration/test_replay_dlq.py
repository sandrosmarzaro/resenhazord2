import json

import aio_pika
import pytest

from bot.adapters.broker.command_consumer import CommandConsumer
from scripts.replay_dlq import DlqReplayer


def _dead_letter(text: str) -> aio_pika.Message:
    envelope = {
        'id': f'corr-{text}',
        'attempts': CommandConsumer.MAX_ATTEMPTS,
        'data': {'text': text, 'jid': 'g@g.us', 'sender_jid': 'u@s.whatsapp.net'},
    }
    return aio_pika.Message(json.dumps(envelope).encode())


@pytest.fixture
async def connection(rabbitmq_url):
    async with await aio_pika.connect(rabbitmq_url) as connection:
        channel = await connection.channel()
        for name in (CommandConsumer.DLQ_QUEUE, CommandConsumer.COMMANDS_QUEUE):
            queue = await channel.declare_queue(name, durable=True)
            await queue.purge()
        for text in ('ping', 'pong'):
            await channel.default_exchange.publish(
                _dead_letter(text), routing_key=CommandConsumer.DLQ_QUEUE
            )
        yield connection


async def _drain(connection, name: str) -> list[dict]:
    channel = await connection.channel()
    queue = await channel.declare_queue(name, durable=True)
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
    async def test_moves_dead_letters_back_to_commands(self, connection):
        replayed = await DlqReplayer(connection).replay()

        commands = await _drain(connection, CommandConsumer.COMMANDS_QUEUE)
        assert replayed == 2
        assert [envelope['data']['text'] for envelope in commands] == ['ping', 'pong']
        assert await _drain(connection, CommandConsumer.DLQ_QUEUE) == []

    @pytest.mark.anyio
    async def test_replayed_commands_restart_the_retry_ladder(self, connection):
        await DlqReplayer(connection).replay()

        commands = await _drain(connection, CommandConsumer.COMMANDS_QUEUE)
        assert {(envelope['attempts'], envelope['replayed']) for envelope in commands} == {
            (0, True)
        }
