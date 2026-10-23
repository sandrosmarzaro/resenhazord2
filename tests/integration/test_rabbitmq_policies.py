import json
from pathlib import Path

import aio_pika
import pytest
from testcontainers.rabbitmq import RabbitMqContainer

from bot.adapters.broker.command_consumer import CommandConsumer

POLICIES_SCRIPT = Path(__file__).parents[2] / 'observability' / 'rabbitmq' / 'policies.sh'
COMMANDS_MAX_LENGTH = 100
WEEK_MS = 7 * 24 * 60 * 60 * 1000


@pytest.fixture(scope='module')
def container():
    with RabbitMqContainer('rabbitmq:3.13') as container:
        # The edge deploy pipes this same script into its broker container.
        result = container.exec(['sh', '-c', POLICIES_SCRIPT.read_text()])
        assert result.exit_code == 0, result.output.decode()
        yield container


@pytest.fixture
async def channel(container):
    params = container.get_connection_params()
    url = f'amqp://{container.username}:{container.password}@{params.host}:{params.port}/'
    async with await aio_pika.connect(url) as connection:
        yield await connection.channel()


class TestCommandsQueue:
    @pytest.mark.anyio
    async def test_a_full_queue_drops_the_oldest_command(self, channel):
        queue = await channel.declare_queue(CommandConsumer.COMMANDS_QUEUE, durable=True)
        for number in range(COMMANDS_MAX_LENGTH + 1):
            message = aio_pika.Message(str(number).encode())
            await channel.default_exchange.publish(message, routing_key=queue.name)

        oldest = await queue.get(no_ack=True)

        assert oldest.body == b'1'


class TestDeadLetterQueue:
    def test_dead_letters_keep_a_week_at_most(self, container):
        command = ['rabbitmqctl', '-q', 'list_policies', '--formatter', 'json']

        policies = json.loads(container.exec(command).output)

        retention = next(policy for policy in policies if policy['name'] == 'dlq-retention')
        assert json.loads(retention['definition'])['message-ttl'] == WEEK_MS
