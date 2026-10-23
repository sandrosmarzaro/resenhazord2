"""Send the dead-lettered commands back to the commands queue.

Runs inside the core bot container, which reaches the edge broker:

    uv run task dlq:replay
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.settings import Settings


class DlqReplayer:
    def __init__(self, connection: aio_pika.abc.AbstractConnection) -> None:
        self._connection = connection

    async def preview(self) -> list[dict[str, Any]]:
        # Unacked gets go back to the queue, in order, when the channel closes.
        async with self._connection.channel() as channel:
            queue = await channel.declare_queue(CommandConsumer.DLQ_QUEUE, durable=True)
            dead_letters = []
            while message := await queue.get(fail=False):
                dead_letters.append(json.loads(message.body))
            return dead_letters

    async def replay(self) -> int:
        async with self._connection.channel(publisher_confirms=True) as channel:
            queue = await channel.declare_queue(CommandConsumer.DLQ_QUEUE, durable=True)
            replayed = 0
            while message := await queue.get(fail=False):
                envelope = {**json.loads(message.body), 'attempts': 0, 'replayed': True}
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        json.dumps(envelope).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=CommandConsumer.COMMANDS_QUEUE,
                )
                await message.ack()
                replayed += 1
            return replayed


async def _with_replayer[T](rabbitmq_url: str, action: Callable[[DlqReplayer], Awaitable[T]]) -> T:
    async with await aio_pika.connect(rabbitmq_url) as connection:
        return await action(DlqReplayer(connection))


def main(rabbitmq_url: str) -> None:
    dead_letters = asyncio.run(_with_replayer(rabbitmq_url, DlqReplayer.preview))
    for envelope in dead_letters:
        data = envelope['data']
        print(f'{envelope["id"]}  {data["jid"]}  {data.get("text")!r}')
    if not dead_letters:
        print('The DLQ is empty.')
        return
    if input(f'Replay {len(dead_letters)} commands? [y/N] ').strip().lower() != 'y':
        return
    replayed = asyncio.run(_with_replayer(rabbitmq_url, DlqReplayer.replay))
    print(f'Replayed {replayed} commands.')


if __name__ == '__main__':
    main(Settings().rabbitmq_url)
