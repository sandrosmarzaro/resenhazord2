from bot.data.broker_topology import DURABLE_QUEUES, RETRY_LADDER
from bot.infrastructure.broker_topology import BrokerTopology


def short_ladder(*ttls_ms: int) -> BrokerTopology:
    # A queue gets its TTL when it is declared, so a broker that saw the real ladder
    # refuses this one: use it on a broker of its own.
    queues = dict(DURABLE_QUEUES)
    for queue, ttl_ms in zip(RETRY_LADDER, ttls_ms, strict=True):
        queues[queue] = queues[queue] | {'x-message-ttl': ttl_ms}
    return BrokerTopology(queues=queues)
