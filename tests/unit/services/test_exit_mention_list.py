import pytest

from bot.domain.models.removal_targets import RemovalTargets
from bot.domain.services.mentions.exit_mention_list import ExitMentionList
from bot.domain.services.mentions.mention_group import MentionGroup

CHAT_JID = '120363044041082732@g.us'
SENDER_JID = '5511999990000@s.whatsapp.net'
OTHER_JID = '5511999990001@s.whatsapp.net'
GROUP_NAME = 'test'


class _StatefulMockCollection:
    """Mock MongoDB collection that actually mutates document state."""

    def __init__(self, initial_docs):
        self._docs = {doc['_id']: doc for doc in initial_docs}

    async def find_one(self, query, projection=None):
        doc_id = query.get('_id')
        doc = self._docs.get(doc_id)
        if doc is None:
            return None

        group_name = query.get('groups.name')
        groups = doc.get('groups', [])
        if group_name is not None and not any(g['name'] == group_name for g in groups):
            return None

        if projection:
            result = {'_id': doc['_id']}
            for key in projection:
                if key == '_id':
                    continue
                if key == 'groups.$':
                    matched = next((g for g in groups if g['name'] == group_name), None)
                    if matched:
                        result['groups'] = [matched]
                else:
                    result[key] = doc.get(key)
            return result

        return doc

    def _resolve_group_idx(self, doc, group_name):
        if group_name is None:
            return None
        for i, g in enumerate(doc.get('groups', [])):
            if g['name'] == group_name:
                return i
        return None

    def _apply_pull(self, doc, group_idx, fields):
        for field_path, value in fields.items():
            if not field_path.startswith('groups.$.') or group_idx is None:
                continue
            subfield = field_path.replace('groups.$.', '')
            arr = doc['groups'][group_idx].get(subfield, [])
            if isinstance(value, dict) and '$in' in value:
                doc['groups'][group_idx][subfield] = [x for x in arr if x not in value['$in']]
            else:
                doc['groups'][group_idx][subfield] = [x for x in arr if x != value]

    async def update_one(self, query, update):
        doc_id = query.get('_id')
        doc = self._docs.get(doc_id)
        if doc is None:
            return

        group_idx = self._resolve_group_idx(doc, query.get('groups.name'))
        if group_idx is None and 'groups.name' in query:
            return

        for operator, fields in update.items():
            if operator == '$pull':
                self._apply_pull(doc, group_idx, fields)


@pytest.fixture
def mock_collection(mocker):
    doc = {
        '_id': CHAT_JID,
        'groups': [
            {
                'name': GROUP_NAME,
                'participants': [SENDER_JID, '5511999990001@s.whatsapp.net'],
            }
        ],
    }
    collection = _StatefulMockCollection([doc])
    mocker.patch(
        'bot.infrastructure.mongodb.MongoDBConnection.collection',
        return_value=collection,
    )
    return collection


class TestExitSelf:
    @pytest.mark.anyio
    async def test_exit_self_removes_sender(self, mock_collection):
        result = await ExitMentionList().execute(CHAT_JID, GROUP_NAME, SENDER_JID, RemovalTargets())

        assert result['ok'] is True

        mention_result = await MentionGroup().execute(CHAT_JID, GROUP_NAME)
        assert SENDER_JID not in mention_result['participants']

    @pytest.mark.anyio
    async def test_exit_self_with_device_suffix_jid(self, mock_collection):
        """Sender JID has device suffix (:1) but stored JID does not."""
        sender_with_device = '5511999990000:1@s.whatsapp.net'

        result = await ExitMentionList().execute(
            CHAT_JID, GROUP_NAME, sender_with_device, RemovalTargets()
        )

        assert result['ok'] is True
        mention_result = await MentionGroup().execute(CHAT_JID, GROUP_NAME)
        assert SENDER_JID not in mention_result['participants']

    @pytest.mark.anyio
    async def test_exit_self_removes_all_duplicates(self, mock_collection):
        """If the sender appears multiple times (legacy data), remove all."""
        mock_collection._docs[CHAT_JID]['groups'][0]['participants'] = [
            SENDER_JID,
            SENDER_JID,
            OTHER_JID,
        ]

        result = await ExitMentionList().execute(CHAT_JID, GROUP_NAME, SENDER_JID, RemovalTargets())

        assert result['ok'] is True
        mention_result = await MentionGroup().execute(CHAT_JID, GROUP_NAME)
        assert SENDER_JID not in mention_result['participants']
        assert OTHER_JID in mention_result['participants']

    @pytest.mark.anyio
    async def test_exit_self_not_in_group_fails(self, mock_collection):
        """Sender is not a participant of the group."""
        stranger = '5511999999999@s.whatsapp.net'

        result = await ExitMentionList().execute(CHAT_JID, GROUP_NAME, stranger, RemovalTargets())

        assert result['ok'] is False
        assert 'não está no grupo' in result['message']


class TestExitByIndices:
    @pytest.mark.anyio
    async def test_exit_by_indices_removes_participants(self, mock_collection):
        result = await ExitMentionList().execute(
            CHAT_JID, GROUP_NAME, SENDER_JID, RemovalTargets(indices=[2])
        )

        assert result['ok'] is True

        mention_result = await MentionGroup().execute(CHAT_JID, GROUP_NAME)
        assert OTHER_JID not in mention_result['participants']
        assert SENDER_JID in mention_result['participants']

    @pytest.mark.anyio
    async def test_exit_invalid_indices_fails(self, mock_collection):
        result = await ExitMentionList().execute(
            CHAT_JID, GROUP_NAME, SENDER_JID, RemovalTargets(indices=[99])
        )

        assert result['ok'] is False


class TestExitByMention:
    @pytest.mark.anyio
    async def test_exit_by_mention_removes_target(self, mock_collection):
        result = await ExitMentionList().execute(
            CHAT_JID, GROUP_NAME, SENDER_JID, RemovalTargets(mentioned=[OTHER_JID])
        )

        assert result['ok'] is True
        assert result['self_only'] is False
        mention_result = await MentionGroup().execute(CHAT_JID, GROUP_NAME)
        assert OTHER_JID not in mention_result['participants']

    @pytest.mark.anyio
    async def test_exit_by_mention_when_sender_not_in_group(self, mock_collection):
        """Sender removing someone else while not a participant themselves."""
        stranger = '5511999999999@s.whatsapp.net'

        result = await ExitMentionList().execute(
            CHAT_JID, GROUP_NAME, stranger, RemovalTargets(mentioned=[OTHER_JID])
        )

        assert result['ok'] is True
        mention_result = await MentionGroup().execute(CHAT_JID, GROUP_NAME)
        assert OTHER_JID not in mention_result['participants']

    @pytest.mark.anyio
    async def test_exit_by_mention_normalizes_device_suffix(self, mock_collection):
        mentioned_with_device = '5511999990001:7@s.whatsapp.net'

        result = await ExitMentionList().execute(
            CHAT_JID, GROUP_NAME, SENDER_JID, RemovalTargets(mentioned=[mentioned_with_device])
        )

        assert result['ok'] is True
        mention_result = await MentionGroup().execute(CHAT_JID, GROUP_NAME)
        assert OTHER_JID not in mention_result['participants']

    @pytest.mark.anyio
    async def test_exit_by_mention_unknown_person_fails(self, mock_collection):
        outsider = '5511900000000@s.whatsapp.net'

        result = await ExitMentionList().execute(
            CHAT_JID, GROUP_NAME, SENDER_JID, RemovalTargets(mentioned=[outsider])
        )

        assert result['ok'] is False
        assert 'Nenhum participante' in result['message']


class TestExitErrors:
    @pytest.mark.anyio
    async def test_exit_nonexistent_group_fails(self, mock_collection):
        result = await ExitMentionList().execute(
            CHAT_JID, 'nonexistent', SENDER_JID, RemovalTargets()
        )

        assert result['ok'] is False
