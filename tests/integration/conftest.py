import pytest
from testcontainers.rabbitmq import RabbitMqContainer


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope='session')
def rabbitmq_url():
    with RabbitMqContainer('rabbitmq:3.13') as container:
        params = container.get_connection_params()
        yield (f'amqp://{container.username}:{container.password}@{params.host}:{params.port}/')
