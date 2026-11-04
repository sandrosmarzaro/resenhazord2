import pytest
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.mongodb import MongoDbContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer
from testcontainers.redis import RedisContainer

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


@pytest.fixture(scope='session')
def redis_url():
    with RedisContainer('redis:7-alpine') as container:
        host = container.get_container_host_ip()
        yield f'redis://{host}:{container.get_exposed_port(6379)}/0'


@pytest.fixture(scope='session')
def postgres_url():
    with PostgresContainer('postgres:17-alpine') as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        yield (
            f'postgresql+asyncpg://{container.username}:{container.password}'
            f'@{host}:{port}/{container.dbname}'
        )
