import httpx
import pytest

from bot.domain.services.steal_group import LOREMFLICKR_URL, StealGroupService

BOT_JID = 'bot@s.whatsapp.net'
RESENHA_JID = 'resenha@g.us'
GROUP_JID = 'target@g.us'


def _group_event(action='promote', participants=None):
    return {
        'id': GROUP_JID,
        'action': action,
        'participants': participants or [{'id': BOT_JID}],
    }


def _metadata(*, participants=None, owner='someone_else@s.whatsapp.net'):
    return {
        'participants': participants
        or [
            {'id': BOT_JID, 'admin': 'superadmin'},
            {'id': 'admin1@s.whatsapp.net', 'admin': 'admin'},
            {'id': 'member@s.whatsapp.net'},
        ],
        'ownerPn': owner,
        'subject': 'Target Group',
        'desc': 'A group',
    }


@pytest.fixture
def service(mock_whatsapp):
    return StealGroupService(mock_whatsapp, BOT_JID, RESENHA_JID)


@pytest.fixture
def colony_collection(mock_mongodb_collection):
    collection = mock_mongodb_collection('colonias')
    collection.find_one_and_update.return_value = {'number': 1}
    return collection


@pytest.fixture
def loremflickr_route(respx_mock):
    return respx_mock.get(url__startswith=LOREMFLICKR_URL).mock(
        return_value=httpx.Response(200, content=b'image-data')
    )


class TestIgnoredActions:
    @pytest.mark.anyio
    async def test_ignores_non_promote(self, service, mock_whatsapp):
        await service.run(_group_event(action='demote'))

        mock_whatsapp.group_metadata.assert_not_called()

    @pytest.mark.anyio
    async def test_ignores_other_participant_promoted(self, service, mock_whatsapp):
        await service.run(_group_event(participants=[{'id': 'other@s.whatsapp.net'}]))

        mock_whatsapp.group_metadata.assert_not_called()


class TestOwnerIsAdmin:
    @pytest.mark.anyio
    async def test_skips_if_owner_is_admin(self, service, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = _metadata(
            participants=[
                {'id': BOT_JID, 'admin': 'superadmin'},
                {'id': 'owner@s.whatsapp.net', 'admin': 'admin'},
            ],
            owner='owner@s.whatsapp.net',
        )

        await service.run(_group_event())

        mock_whatsapp.group_participants_update.assert_not_called()


class TestStealExecution:
    @pytest.mark.anyio
    async def test_demotes_admins_and_renames(
        self, service, mock_whatsapp, colony_collection, loremflickr_route
    ):
        mock_whatsapp.group_metadata.return_value = _metadata()

        await service.run(_group_event())

        mock_whatsapp.group_participants_update.assert_called_once_with(
            GROUP_JID, ['admin1@s.whatsapp.net'], 'demote'
        )
        mock_whatsapp.group_update_subject.assert_called_once_with(
            GROUP_JID, 'Colônia da Resenha I 🐮🎣🍆'
        )
        mock_whatsapp.send_message.assert_called_once()
        call_args = mock_whatsapp.send_message.call_args
        assert call_args[0][0] == RESENHA_JID
        assert 'Colônia obtida!' in call_args[0][1]['text']
        assert 'Target Group' in call_args[0][1]['text']
        mock_whatsapp.group_update_description.assert_called_once()
        mock_whatsapp.update_profile_picture.assert_called_once_with(GROUP_JID, b'image-data')

    @pytest.mark.anyio
    async def test_roman_numeral_increments(
        self, service, mock_whatsapp, colony_collection, loremflickr_route
    ):
        mock_whatsapp.group_metadata.return_value = _metadata(
            participants=[{'id': BOT_JID, 'admin': 'superadmin'}],
            owner='',
        )
        colony_collection.find_one_and_update.return_value = {'number': 42}

        await service.run(_group_event())

        subject_call = mock_whatsapp.group_update_subject.call_args[0][1]
        assert 'XLII' in subject_call

    @pytest.mark.anyio
    async def test_error_does_not_propagate(self, service, mock_whatsapp):
        mock_whatsapp.group_metadata.side_effect = RuntimeError('network error')

        # Should not raise
        await service.run(_group_event())
