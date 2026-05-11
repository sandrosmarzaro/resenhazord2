import pytest

from bot.domain.services.mentions.add_to_mention_list import AddToMentionList
from bot.domain.services.mentions.create_mention_list import CreateMentionList

CHAT_JID = '120363044041082732@g.us'
SENDER_JID = '5511999990000:1@s.whatsapp.net'
GROUP_NAME = 'devs'


class _MockCollection:
    """Minimal mock that records calls for assertion."""

    def __init__(self):
        self.docs = {}
        self.calls = []

    async def find_one(self, query):
        self.calls.append(('find_one', query))
        doc_id = query.get('_id')
        doc = self.docs.get(doc_id)
        if doc is None:
            return None
        group_name = query.get('groups.name')
        if group_name is not None and not any(
            g['name'] == group_name for g in doc.get('groups', [])
        ):
            return None
        return doc

    async def insert_one(self, doc):
        self.calls.append(('insert_one', doc))
        self.docs[doc['_id']] = doc

    async def update_one(self, query, update):
        self.calls.append(('update_one', query, update))


@pytest.fixture
def mock_collection(mocker):
    collection = _MockCollection()
    mocker.patch(
        'bot.infrastructure.mongodb.MongoDBConnection.collection',
        return_value=collection,
    )
    return collection


class TestCreateMentionList:
    @pytest.mark.anyio
    async def test_creates_group_with_normalized_jids(self, mock_collection):
        result = await CreateMentionList().execute(
            CHAT_JID,
            SENDER_JID,
            GROUP_NAME,
            ['5511999990001:2@s.whatsapp.net'],
        )

        assert result['ok'] is True
        assert result['group_name'] == GROUP_NAME

        _, doc = mock_collection.calls[2]
        participants = doc['groups'][0]['participants']
        assert participants == [
            '5511999990000@s.whatsapp.net',
            '5511999990001@s.whatsapp.net',
        ]

    @pytest.mark.anyio
    async def test_rejects_duplicate_group(self, mock_collection):
        mock_collection.docs[CHAT_JID] = {
            '_id': CHAT_JID,
            'groups': [{'name': GROUP_NAME, 'participants': []}],
        }

        result = await CreateMentionList().execute(CHAT_JID, SENDER_JID, GROUP_NAME, [])

        assert result['ok'] is False
        assert 'Já existe' in result['message']


class TestAddToMentionList:
    @pytest.mark.anyio
    async def test_adds_self_with_normalized_jid(self, mock_collection):
        mock_collection.docs[CHAT_JID] = {
            '_id': CHAT_JID,
            'groups': [{'name': GROUP_NAME, 'participants': []}],
        }

        result = await AddToMentionList().execute(CHAT_JID, GROUP_NAME, SENDER_JID, [])

        assert result['ok'] is True
        _, _, update = mock_collection.calls[1]
        assert update['$addToSet']['groups.$.participants'] == '5511999990000@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_adds_others_with_normalized_jids(self, mock_collection):
        mock_collection.docs[CHAT_JID] = {
            '_id': CHAT_JID,
            'groups': [{'name': GROUP_NAME, 'participants': []}],
        }

        result = await AddToMentionList().execute(
            CHAT_JID,
            GROUP_NAME,
            SENDER_JID,
            ['5511999990001:2@s.whatsapp.net'],
        )

        assert result['ok'] is True
        _, _, update = mock_collection.calls[1]
        assert update['$addToSet']['groups.$.participants']['$each'] == [
            '5511999990001@s.whatsapp.net',
        ]

    @pytest.mark.anyio
    async def test_rejects_nonexistent_group(self, mock_collection):
        result = await AddToMentionList().execute(CHAT_JID, GROUP_NAME, SENDER_JID, [])

        assert result['ok'] is False
        assert 'Não existe' in result['message']
