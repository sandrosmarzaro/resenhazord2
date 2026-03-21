from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.domain.services.steal_group import StealGroupService

BOT_JID = 'bot@s.whatsapp.net'
RESENHA_JID = 'resenha@g.us'
GROUP_JID = 'target@g.us'


@pytest.fixture
def mock_whatsapp():
    wa = MagicMock()
    wa.group_metadata = AsyncMock()
    wa.group_participants_update = AsyncMock()
    wa.group_update_subject = AsyncMock()
    wa.group_update_description = AsyncMock()
    wa.send_message = AsyncMock()
    wa.update_profile_picture = AsyncMock()
    return wa


@pytest.fixture
def service(mock_whatsapp):
    return StealGroupService(mock_whatsapp, BOT_JID, RESENHA_JID)


def _group_event(action='promote', participants=None):
    return {
        'id': GROUP_JID,
        'action': action,
        'participants': participants or [{'id': BOT_JID}],
    }


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
        mock_whatsapp.group_metadata.return_value = {
            'participants': [
                {'id': BOT_JID, 'admin': 'superadmin'},
                {'id': 'owner@s.whatsapp.net', 'admin': 'admin'},
            ],
            'ownerPn': 'owner@s.whatsapp.net',
            'subject': 'Test',
            'desc': '',
        }

        await service.run(_group_event())

        mock_whatsapp.group_participants_update.assert_not_called()


class TestStealExecution:
    @pytest.mark.anyio
    async def test_demotes_admins_and_renames(self, service, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [
                {'id': BOT_JID, 'admin': 'superadmin'},
                {'id': 'admin1@s.whatsapp.net', 'admin': 'admin'},
                {'id': 'member@s.whatsapp.net'},
            ],
            'ownerPn': 'someone_else@s.whatsapp.net',
            'subject': 'Target Group',
            'desc': 'A group',
        }

        mock_collection = AsyncMock()
        mock_collection.find_one_and_update.return_value = {'number': 1}

        with (
            patch(
                'bot.domain.services.steal_group.MongoDBConnection.collection',
                return_value=mock_collection,
            ),
            patch(
                'bot.domain.services.steal_group.HttpClient.get_buffer',
                new_callable=AsyncMock,
                return_value=b'image-data',
            ),
        ):
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
    async def test_roman_numeral_increments(self, service, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': BOT_JID, 'admin': 'superadmin'}],
            'ownerPn': '',
            'subject': 'G',
            'desc': '',
        }

        mock_collection = AsyncMock()
        mock_collection.find_one_and_update.return_value = {'number': 42}

        with (
            patch(
                'bot.domain.services.steal_group.MongoDBConnection.collection',
                return_value=mock_collection,
            ),
            patch(
                'bot.domain.services.steal_group.HttpClient.get_buffer',
                new_callable=AsyncMock,
                return_value=b'img',
            ),
        ):
            await service.run(_group_event())

        subject_call = mock_whatsapp.group_update_subject.call_args[0][1]
        assert 'XLII' in subject_call

    @pytest.mark.anyio
    async def test_error_does_not_propagate(self, service, mock_whatsapp):
        mock_whatsapp.group_metadata.side_effect = RuntimeError('network error')

        # Should not raise
        await service.run(_group_event())
