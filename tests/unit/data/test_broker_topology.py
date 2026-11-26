import json
from pathlib import Path

from bot.data.broker_topology import BINDINGS, DURABLE_QUEUES, TOPIC_EXCHANGES

GATEWAY_TOPOLOGY = Path(__file__).parents[3] / 'gateway' / 'src' / 'data' / 'BrokerTopology.json'


def test_matches_the_topology_the_gateway_declares():
    gateway = json.loads(GATEWAY_TOPOLOGY.read_text())

    assert gateway == {
        'exchanges': list(TOPIC_EXCHANGES),
        'queues': DURABLE_QUEUES,
        'bindings': [
            {'exchange': exchange, 'pattern': pattern, 'queue': queue}
            for exchange, pattern, queue in BINDINGS
        ],
    }
