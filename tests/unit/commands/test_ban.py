import pytest

from bot.domain.commands.ban import BanCommand
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command(mock_whatsapp):
    return BanCommand(bot_jid='5500000000000@s.whatsapp.net', whatsapp=mock_whatsapp)


def _make_participants(*jids, bot_admin=True, owner=None, owner_admin=False):
    bot_jid = '5500000000000@s.whatsapp.net'
    participants = []
    for jid in jids:
        entry = {'id': jid, 'admin': None}
        if jid == bot_jid and bot_admin:
            entry['admin'] = 'admin'
        if jid == owner and owner_admin:
            entry['admin'] = 'admin'
        participants.append(entry)
    return {'participants': participants, 'owner': owner}


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',ban', True),
            (', ban', True),
            (', BAN', True),
            (', ban @5511999990001', True),
            ('ban', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestGroupOnly:
    @pytest.mark.anyio
    async def test_rejects_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=',ban')
        messages = await command.run(data)

        assert 'só funciona em grupo' in messages[0].content.text


class TestBotNotAdmin:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'

    @pytest.mark.anyio
    async def test_bot_not_admin(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = _make_participants(
            self.BOT_JID, '5511999990001@s.whatsapp.net', bot_admin=False
        )
        data = GroupCommandDataFactory.build(text=',ban', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert 'não sou admin' in messages[0].content.text


class TestBanRandom:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'
    OWNER_JID = '5511999990099@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_bans_random_participant(self, command, mock_whatsapp):
        target_jid = '5511999990001@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = _make_participants(self.BOT_JID, target_jid)
        data = GroupCommandDataFactory.build(text=',ban', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'Se fudeu!' in messages[0].content.text
        assert '@5511999990001' in messages[0].content.text
        mock_whatsapp.group_participants_update.assert_called_once_with(
            self.CHAT_JID, [target_jid], 'remove'
        )

    @pytest.mark.anyio
    async def test_skips_bot_and_owner(self, command, mock_whatsapp):
        target_jid = '5511999990001@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = _make_participants(
            self.BOT_JID, self.OWNER_JID, target_jid, owner=self.OWNER_JID
        )
        data = GroupCommandDataFactory.build(text=',ban', jid=self.CHAT_JID)

        messages = await command.run(data)

        # Should skip bot and owner, ban the target
        assert len(messages) == 1
        call_args = mock_whatsapp.group_participants_update.call_args
        assert call_args[0][1] == [target_jid]


class TestBanMentioned:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'
    OWNER_JID = '5511999990099@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_bans_mentioned_participants(self, command, mock_whatsapp):
        target1 = '5511999990001@s.whatsapp.net'
        target2 = '5511999990002@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = _make_participants(
            self.BOT_JID, target1, target2
        )
        data = GroupCommandDataFactory.build(
            text=',ban @5511999990001 @5511999990002',
            jid=self.CHAT_JID,
            mentioned_jids=[target1, target2],
        )

        messages = await command.run(data)

        assert len(messages) == 2
        assert mock_whatsapp.group_participants_update.call_count == 2

    @pytest.mark.anyio
    async def test_skips_bot_in_mentioned(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = _make_participants(self.BOT_JID)
        data = GroupCommandDataFactory.build(
            text=',ban @5500000000000',
            jid=self.CHAT_JID,
            mentioned_jids=[self.BOT_JID],
        )

        messages = await command.run(data)

        assert len(messages) == 0
        mock_whatsapp.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_admin_owner_in_mentioned(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = _make_participants(
            self.BOT_JID, self.OWNER_JID, owner=self.OWNER_JID, owner_admin=True
        )
        data = GroupCommandDataFactory.build(
            text=',ban @5511999990099',
            jid=self.CHAT_JID,
            mentioned_jids=[self.OWNER_JID],
        )

        messages = await command.run(data)

        assert len(messages) == 0
        mock_whatsapp.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_allows_non_admin_owner_in_mentioned(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = _make_participants(
            self.BOT_JID, self.OWNER_JID, owner=self.OWNER_JID, owner_admin=False
        )
        data = GroupCommandDataFactory.build(
            text=',ban @5511999990099',
            jid=self.CHAT_JID,
            mentioned_jids=[self.OWNER_JID],
        )

        messages = await command.run(data)

        assert len(messages) == 1
        mock_whatsapp.group_participants_update.assert_called_once()

    @pytest.mark.anyio
    async def test_strips_jid_suffix(self, command, mock_whatsapp):
        target = '5511999990001@lid'
        mock_whatsapp.group_metadata.return_value = _make_participants(self.BOT_JID, target)
        data = GroupCommandDataFactory.build(
            text=',ban @5511999990001',
            jid=self.CHAT_JID,
            mentioned_jids=[target],
        )

        messages = await command.run(data)

        assert '@5511999990001' in messages[0].content.text


class TestBanError:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'

    @pytest.mark.anyio
    async def test_random_ban_error(self, command, mock_whatsapp):
        target_jid = '5511999990001@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = _make_participants(self.BOT_JID, target_jid)
        mock_whatsapp.group_participants_update.side_effect = Exception('API error')
        data = GroupCommandDataFactory.build(text=',ban', jid=self.CHAT_JID)

        messages = await command.run(data)

        # On error, no success message
        assert len(messages) == 0

    @pytest.mark.anyio
    async def test_mentioned_ban_error_continues(self, command, mock_whatsapp):
        target1 = '5511999990001@s.whatsapp.net'
        target2 = '5511999990002@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = _make_participants(
            self.BOT_JID, target1, target2
        )
        mock_whatsapp.group_participants_update.side_effect = [
            Exception('API error'),
            [],
        ]
        data = GroupCommandDataFactory.build(
            text=',ban @5511999990001 @5511999990002',
            jid=self.CHAT_JID,
            mentioned_jids=[target1, target2],
        )

        messages = await command.run(data)

        # First fails, second succeeds
        assert len(messages) == 1
        assert '@5511999990002' in messages[0].content.text
