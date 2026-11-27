from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

import aio_pika

from bot.data.broker_topology import (
    BINDINGS,
    DEAD_LETTER_EXCHANGE,
    DEAD_LETTER_ROUTES,
    DURABLE_QUEUES,
    TOPIC_EXCHANGES,
)


@dataclass(frozen=True)
class BrokerTopology:
    # all-with-x: a plain headers match skips every header that starts with x-.
    DEATH_MATCH: ClassVar[str] = 'all-with-x'

    exchanges: tuple[str, ...] = TOPIC_EXCHANGES
    queues: Mapping[str, Mapping[str, int | str]] = DURABLE_QUEUES
    bindings: tuple[tuple[str, str, str], ...] = BINDINGS
    dead_letter_routes: Mapping[str, str] = DEAD_LETTER_ROUTES

    async def declare(self, channel: aio_pika.abc.AbstractChannel) -> None:
        # Every declare is idempotent, and a robust channel replays them after a reconnect.
        exchanges = {
            name: await channel.declare_exchange(name, aio_pika.ExchangeType.TOPIC, durable=True)
            for name in self.exchanges
        }
        queues = {
            name: await channel.declare_queue(name, durable=True, arguments=dict(arguments))
            for name, arguments in self.queues.items()
        }
        for exchange, pattern, queue in self.bindings:
            await queues[queue].bind(exchanges[exchange], pattern)
        dead_letters = await channel.declare_exchange(
            DEAD_LETTER_EXCHANGE, aio_pika.ExchangeType.HEADERS, durable=True
        )
        destinations = {**exchanges, **queues}
        for reason, destination in self.dead_letter_routes.items():
            # Same empty key as the gateway's bind, so the two nodes make one binding, not two.
            await destinations[destination].bind(
                dead_letters,
                '',
                arguments={'x-match': self.DEATH_MATCH, 'x-last-death-reason': reason},
            )

    def arguments(self, queue: str) -> aio_pika.abc.Arguments:
        # Redeclaring a queue without the arguments it was declared with fails.
        return dict(self.queues.get(queue, {}))
