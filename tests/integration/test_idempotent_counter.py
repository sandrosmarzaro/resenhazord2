import pytest
from testcontainers.mongodb import MongoDbContainer

from bot.domain.commands.borges import BorgesCommand
from bot.infrastructure.mongodb import MongoDBConnection
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture(scope='module')
def mongo_uri():
    with MongoDbContainer('mongo:7') as container:
        yield container.get_connection_url()


@pytest.fixture
async def mongo(mongo_uri):
    MongoDBConnection.reset()
    MongoDBConnection.configure(mongo_uri, db_name='idempotent_counter_test')
    await MongoDBConnection.client().drop_database('idempotent_counter_test')
    yield
    await MongoDBConnection.close()


class TestBorgesRedelivery:
    @pytest.mark.anyio
    async def test_redelivered_message_counts_once(self, mongo):
        command = BorgesCommand()
        data = GroupCommandDataFactory.build(text=',borges', message_id='MSG-1')

        await command.run(data)
        messages = await command.run(data)

        assert 'Borges já fumou 1 nargas' in messages[0].content.text

    @pytest.mark.anyio
    async def test_distinct_messages_each_count(self, mongo):
        command = BorgesCommand()
        first = GroupCommandDataFactory.build(text=',borges', message_id='MSG-1')
        second = GroupCommandDataFactory.build(text=',borges', message_id='MSG-2')

        await command.run(first)
        messages = await command.run(second)

        assert 'Borges já fumou 2 nargas' in messages[0].content.text

    @pytest.mark.anyio
    async def test_messages_without_id_always_count(self, mongo):
        command = BorgesCommand()
        data = GroupCommandDataFactory.build(text=',borges', message_id=None)

        await command.run(data)
        messages = await command.run(data)

        assert 'Borges já fumou 2 nargas' in messages[0].content.text
