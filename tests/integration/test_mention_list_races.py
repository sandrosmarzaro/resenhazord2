import asyncio

import pytest
from testcontainers.mongodb import MongoDbContainer

from bot.domain.services.mentions.create_mention_list import CreateMentionList
from bot.domain.services.mentions.rename_mention_list import RenameMentionList
from bot.infrastructure.mongodb import MongoDBConnection

CHAT_JID = '120363044041082732@g.us'
SENDER_JID = '5511999990000@s.whatsapp.net'
OTHER_JID = '5511999990001:2@s.whatsapp.net'
DATABASE = 'mention_list_races_test'
COLLECTION = 'groups_mentions'
# One round can pass by luck of scheduling; twenty can't.
ROUNDS = 20


@pytest.fixture(scope='module')
def mongo_uri():
    with MongoDbContainer('mongo:7') as container:
        yield container.get_connection_url()


@pytest.fixture
async def collection(mongo_uri):
    MongoDBConnection.reset()
    MongoDBConnection.configure(mongo_uri, db_name=DATABASE)
    yield MongoDBConnection.collection(COLLECTION)
    await MongoDBConnection.close()


async def _seed(collection, *names: str) -> None:
    await collection.delete_many({})
    groups = [{'name': name, 'participants': [SENDER_JID]} for name in names]
    await collection.insert_one({'_id': CHAT_JID, 'groups': groups})


async def _names(collection) -> list[str]:
    document = await collection.find_one({'_id': CHAT_JID})
    return sorted(group['name'] for group in document['groups'])


def _oks(results: list[dict]) -> int:
    return sum(result['ok'] for result in results)


class TestCreate:
    @pytest.mark.anyio
    async def test_same_name_in_an_existing_chat_creates_one_group(self, collection):
        create = CreateMentionList()
        for _ in range(ROUNDS):
            await _seed(collection)

            results = await asyncio.gather(
                *(create.execute(CHAT_JID, SENDER_JID, 'devs', []) for _ in range(2))
            )

            assert await _names(collection) == ['devs']
            assert _oks(results) == 1

    @pytest.mark.anyio
    async def test_same_name_in_a_new_chat_creates_one_group(self, collection):
        create = CreateMentionList()
        for _ in range(ROUNDS):
            await collection.delete_many({})

            results = await asyncio.gather(
                *(create.execute(CHAT_JID, SENDER_JID, 'devs', []) for _ in range(2))
            )

            assert await _names(collection) == ['devs']
            assert _oks(results) == 1

    @pytest.mark.anyio
    async def test_different_names_in_a_new_chat_create_both(self, collection):
        create = CreateMentionList()
        for _ in range(ROUNDS):
            await collection.delete_many({})

            results = await asyncio.gather(
                create.execute(CHAT_JID, SENDER_JID, 'devs', []),
                create.execute(CHAT_JID, SENDER_JID, 'ops', []),
            )

            assert await _names(collection) == ['devs', 'ops']
            assert _oks(results) == len(results)

    @pytest.mark.anyio
    async def test_stores_normalized_jids_and_skips_null_mentions(self, collection):
        await collection.delete_many({})

        result = await CreateMentionList().execute(
            CHAT_JID, '5511999990000:1@s.whatsapp.net', 'devs', [None, OTHER_JID]
        )

        document = await collection.find_one({'_id': CHAT_JID})
        assert result['ok'] is True
        assert document['groups'][0]['participants'] == [SENDER_JID, '5511999990001@s.whatsapp.net']

    @pytest.mark.anyio
    async def test_taken_name_is_refused(self, collection):
        await _seed(collection, 'devs')

        result = await CreateMentionList().execute(CHAT_JID, SENDER_JID, 'devs', [])

        assert result['ok'] is False
        assert 'Já existe' in result['message']


class TestRename:
    @pytest.mark.anyio
    async def test_two_groups_to_one_name_renames_only_one(self, collection):
        rename = RenameMentionList()
        for _ in range(ROUNDS):
            await _seed(collection, 'first', 'second')

            results = await asyncio.gather(
                rename.execute(CHAT_JID, 'first', 'target'),
                rename.execute(CHAT_JID, 'second', 'target'),
            )

            assert (await _names(collection)).count('target') == 1
            assert _oks(results) == 1

    @pytest.mark.anyio
    async def test_same_rename_twice_succeeds_once(self, collection):
        rename = RenameMentionList()
        for _ in range(ROUNDS):
            await _seed(collection, 'first')

            results = await asyncio.gather(
                *(rename.execute(CHAT_JID, 'first', 'target') for _ in range(2))
            )

            assert await _names(collection) == ['target']
            assert _oks(results) == 1

    @pytest.mark.anyio
    async def test_missing_group_is_refused(self, collection):
        await _seed(collection, 'first')

        result = await RenameMentionList().execute(CHAT_JID, 'ghost', 'target')

        assert result['ok'] is False
        assert 'Não existe' in result['message']

    @pytest.mark.anyio
    async def test_taken_name_is_refused(self, collection):
        await _seed(collection, 'first', 'second')

        result = await RenameMentionList().execute(CHAT_JID, 'first', 'second')

        assert result['ok'] is False
        assert 'Já existe' in result['message']
        assert await _names(collection) == ['first', 'second']
