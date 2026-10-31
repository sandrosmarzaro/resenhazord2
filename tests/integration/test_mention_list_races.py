import asyncio

import pytest
from testcontainers.mongodb import MongoDbContainer

from bot.domain.models.removal_targets import RemovalTargets
from bot.domain.services.mentions.add_to_mention_list import AddToMentionList
from bot.domain.services.mentions.create_mention_list import CreateMentionList
from bot.domain.services.mentions.delete_mention_list import DeleteMentionList
from bot.domain.services.mentions.exit_mention_list import ExitMentionList
from bot.domain.services.mentions.rename_mention_list import RenameMentionList
from bot.infrastructure.mongodb import MongoDBConnection

CHAT_JID = '120363044041082732@g.us'
SENDER_JID = '5511999990000@s.whatsapp.net'
OTHER_JID = '5511999990001:2@s.whatsapp.net'
OTHER_NORMALIZED_JID = '5511999990001@s.whatsapp.net'
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


async def _participants(collection, name: str = 'devs') -> list[str]:
    document = await collection.find_one({'_id': CHAT_JID})
    return next(g['participants'] for g in document['groups'] if g['name'] == name)


def _oks(results: list[dict]) -> int:
    return sum(result['ok'] for result in results)


class _VanishingGroupCollection:
    # Deletes the group right before the next write lands, the one interleaving that a
    # read-then-write service would answer with a false success.
    def __init__(self, collection) -> None:
        self._collection = collection

    def __getattr__(self, name: str):
        return getattr(self._collection, name)

    async def update_one(self, query: dict, update: dict):
        await self._collection.update_one({'_id': CHAT_JID}, {'$set': {'groups': []}})
        return await self._collection.update_one(query, update)


@pytest.fixture
def vanishing_group(collection, mocker):
    mocker.patch(
        'bot.infrastructure.mongodb.MongoDBConnection.collection',
        return_value=_VanishingGroupCollection(collection),
    )


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
        assert document['groups'][0]['participants'] == [SENDER_JID, OTHER_NORMALIZED_JID]

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


class TestDelete:
    @pytest.mark.anyio
    async def test_same_delete_twice_succeeds_once(self, collection):
        delete = DeleteMentionList()
        for _ in range(ROUNDS):
            await _seed(collection, 'devs', 'ops')

            results = await asyncio.gather(*(delete.execute(CHAT_JID, 'devs') for _ in range(2)))

            assert await _names(collection) == ['ops']
            assert _oks(results) == 1

    @pytest.mark.anyio
    async def test_missing_group_is_refused(self, collection):
        await _seed(collection, 'ops')

        result = await DeleteMentionList().execute(CHAT_JID, 'devs')

        assert result['ok'] is False
        assert 'Não existe' in result['message']


class TestAdd:
    @pytest.mark.anyio
    async def test_group_deleted_before_the_write_is_refused(self, collection, vanishing_group):
        await _seed(collection, 'devs')

        result = await AddToMentionList().execute(CHAT_JID, 'devs', SENDER_JID, [OTHER_JID])

        assert result['ok'] is False
        assert 'Não existe' in result['message']

    @pytest.mark.anyio
    async def test_same_add_twice_stores_one_participant(self, collection):
        add = AddToMentionList()
        for _ in range(ROUNDS):
            await _seed(collection, 'devs')

            results = await asyncio.gather(
                *(add.execute(CHAT_JID, 'devs', SENDER_JID, [OTHER_JID]) for _ in range(2))
            )

            assert await _participants(collection) == [SENDER_JID, OTHER_NORMALIZED_JID]
            assert _oks(results) == len(results)

    @pytest.mark.anyio
    async def test_no_mentions_adds_the_sender_normalized(self, collection):
        await _seed(collection, 'devs')
        await collection.update_one({'_id': CHAT_JID}, {'$set': {'groups.0.participants': []}})

        result = await AddToMentionList().execute(
            CHAT_JID, 'devs', '5511999990000:1@s.whatsapp.net', []
        )

        assert result == {'ok': True, 'group_name': 'devs', 'self_only': True}
        assert await _participants(collection) == [SENDER_JID]

    @pytest.mark.anyio
    async def test_mentions_are_normalized_and_nulls_skipped(self, collection):
        await _seed(collection, 'devs')

        result = await AddToMentionList().execute(CHAT_JID, 'devs', SENDER_JID, [None, OTHER_JID])

        assert result == {'ok': True, 'group_name': 'devs', 'self_only': False}
        assert await _participants(collection) == [SENDER_JID, OTHER_NORMALIZED_JID]

    @pytest.mark.anyio
    async def test_missing_group_is_refused(self, collection):
        await _seed(collection, 'ops')

        result = await AddToMentionList().execute(CHAT_JID, 'devs', SENDER_JID, [])

        assert result['ok'] is False
        assert 'Não existe' in result['message']


class TestExit:
    @pytest.mark.anyio
    async def test_same_self_exit_twice_succeeds_once(self, collection):
        leave = ExitMentionList()
        for _ in range(ROUNDS):
            await _seed(collection, 'devs')

            results = await asyncio.gather(
                *(leave.execute(CHAT_JID, 'devs', SENDER_JID, RemovalTargets()) for _ in range(2))
            )

            assert await _participants(collection) == []
            assert _oks(results) == 1

    @pytest.mark.anyio
    async def test_same_removal_by_mention_twice_succeeds_once(self, collection):
        targets = RemovalTargets(mentioned=[SENDER_JID])
        leave = ExitMentionList()
        for _ in range(ROUNDS):
            await _seed(collection, 'devs')

            results = await asyncio.gather(
                *(leave.execute(CHAT_JID, 'devs', OTHER_JID, targets) for _ in range(2))
            )

            assert await _participants(collection) == []
            assert _oks(results) == 1

    @pytest.mark.anyio
    async def test_self_exit_of_a_group_deleted_before_the_write_is_refused(
        self, collection, vanishing_group
    ):
        await _seed(collection, 'devs')

        result = await ExitMentionList().execute(CHAT_JID, 'devs', SENDER_JID, RemovalTargets())

        assert result['ok'] is False

    @pytest.mark.anyio
    async def test_removal_of_a_group_deleted_before_the_write_is_refused(
        self, collection, vanishing_group
    ):
        await _seed(collection, 'devs')

        result = await ExitMentionList().execute(
            CHAT_JID, 'devs', OTHER_JID, RemovalTargets(mentioned=[SENDER_JID])
        )

        assert result['ok'] is False
