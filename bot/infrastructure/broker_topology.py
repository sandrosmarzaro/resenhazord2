from collections.abc import Mapping
from dataclasses import dataclass

import aio_pika

from bot.data.broker_topology import BINDINGS, DURABLE_QUEUES, TOPIC_EXCHANGES


@dataclass(frozen=True)
class BrokerTopology:
    exchanges: tuple[str, ...] = TOPIC_EXCHANGES
    queues: Mapping[str, Mapping[str, int | str]] = DURABLE_QUEUES
    bindings: tuple[tuple[str, str, str], ...] = BINDINGS

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
