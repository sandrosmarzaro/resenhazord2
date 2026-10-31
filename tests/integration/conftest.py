import pytest
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.mongodb import MongoDbContainer
from testcontainers.rabbitmq import RabbitMqContainer

# The image logs this once from a temporary server it shuts down to set up the root user,
# then again from the real one. The container's own wait stops at the first.
MONGO_READY_LOG = 'Waiting for connections'
MONGO_READY_COUNT = 2


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope='session')
def rabbitmq_url():
    with RabbitMqContainer('rabbitmq:3.13') as container:
        params = container.get_connection_params()
        yield (f'amqp://{container.username}:{container.password}@{params.host}:{params.port}/')


@pytest.fixture(scope='session')
def mongo_uri():
    with MongoDbContainer('mongo:7') as container:
        wait_for_logs(container, lambda logs: logs.count(MONGO_READY_LOG) >= MONGO_READY_COUNT)
        yield container.get_connection_url()
