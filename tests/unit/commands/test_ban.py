import pytest
from structlog.testing import capture_logs

from bot.domain.commands.ban import BanCommand
from tests.conftest import make_group_participants
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command(ban_command_instance):
    return ban_command_instance


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
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, '5511999990001@s.whatsapp.net', bot_admin=False
        )
        data = GroupCommandDataFactory.build(is_admin=True, text=',ban', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert 'não sou admin' in messages[0].content.text


class TestBanRandom:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'
    OWNER_JID = '5511999990099@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_bans_random_participant(self, command, mock_whatsapp):
        target_jid = '5511999990001@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, target_jid
        )
        data = GroupCommandDataFactory.build(is_admin=True, text=',ban', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'Já era!' in messages[0].content.text
        assert '@5511999990001' in messages[0].content.text
        assert messages[0].content.mentions == [target_jid]
        mock_whatsapp.group_participants_update.assert_called_once_with(
            self.CHAT_JID, [target_jid], 'remove'
        )

    @pytest.mark.anyio
    async def test_a_failed_removal_logs_the_chat_and_replies_nothing(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, '5511999990001@s.whatsapp.net'
        )
        mock_whatsapp.group_participants_update.side_effect = RuntimeError('not allowed')
        data = GroupCommandDataFactory.build(is_admin=True, text=',ban', jid=self.CHAT_JID)

        with capture_logs() as logs:
            messages = await command.run(data)

        assert messages == []
        assert [(log['event'], log['jid']) for log in logs if log['log_level'] == 'error'] == [
            ('ban_random_error', self.CHAT_JID)
        ]

    @pytest.mark.anyio
    async def test_skips_bot_and_owner(self, command, mock_whatsapp):
        target_jid = '5511999990001@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, self.OWNER_JID, target_jid, owner=self.OWNER_JID
        )
        data = GroupCommandDataFactory.build(is_admin=True, text=',ban', jid=self.CHAT_JID)

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
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, target1, target2
        )
        data = GroupCommandDataFactory.build(
            is_admin=True,
            text=',ban @5511999990001 @5511999990002',
            jid=self.CHAT_JID,
            mentioned_jids=[target1, target2],
        )

        messages = await command.run(data)

        assert len(messages) == 2
        assert mock_whatsapp.group_participants_update.call_count == 2

    @pytest.mark.anyio
    async def test_skips_bot_in_mentioned(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(self.BOT_JID)
        data = GroupCommandDataFactory.build(
            is_admin=True,
            text=',ban @5500000000000',
            jid=self.CHAT_JID,
            mentioned_jids=[self.BOT_JID],
        )

        messages = await command.run(data)

        assert len(messages) == 0
        mock_whatsapp.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_admin_owner_in_mentioned(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, self.OWNER_JID, owner=self.OWNER_JID, owner_admin=True
        )
        data = GroupCommandDataFactory.build(
            is_admin=True,
            text=',ban @5511999990099',
            jid=self.CHAT_JID,
            mentioned_jids=[self.OWNER_JID],
        )

        messages = await command.run(data)

        assert len(messages) == 0
        mock_whatsapp.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_allows_non_admin_owner_in_mentioned(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, self.OWNER_JID, owner=self.OWNER_JID, owner_admin=False
        )
        data = GroupCommandDataFactory.build(
            is_admin=True,
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
        mock_whatsapp.group_metadata.return_value = make_group_participants(self.BOT_JID, target)
        data = GroupCommandDataFactory.build(
            is_admin=True,
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
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, target_jid
        )
        mock_whatsapp.group_participants_update.side_effect = Exception('API error')
        data = GroupCommandDataFactory.build(is_admin=True, text=',ban', jid=self.CHAT_JID)

        messages = await command.run(data)

        # On error, no success message
        assert len(messages) == 0

    @pytest.mark.anyio
    async def test_mentioned_ban_error_continues(self, command, mock_whatsapp):
        target1 = '5511999990001@s.whatsapp.net'
        target2 = '5511999990002@s.whatsapp.net'
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, target1, target2
        )
        mock_whatsapp.group_participants_update.side_effect = [
            Exception('API error'),
            [],
        ]
        data = GroupCommandDataFactory.build(
            is_admin=True,
            text=',ban @5511999990001 @5511999990002',
            jid=self.CHAT_JID,
            mentioned_jids=[target1, target2],
        )

        messages = await command.run(data)

        # First fails, second succeeds
        assert len(messages) == 1
        assert '@5511999990002' in messages[0].content.text


class TestAdminOnly:
    BOT_JID = '5500000000000@s.whatsapp.net'
    MEMBER_JID = '5511999990001@s.whatsapp.net'
    TARGET_JID = '5511999990002@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_a_member_is_refused(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, self.MEMBER_JID, self.TARGET_JID
        )
        data = GroupCommandDataFactory.build(
            text=',ban', sender_jid=self.MEMBER_JID, mentioned_jids=[self.TARGET_JID]
        )

        messages = await command.run(data)

        assert messages[0].content.text == 'Só admin pode usar esse comando. 🙅'
        mock_whatsapp.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_an_admin_found_in_the_group_is_allowed(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, self.MEMBER_JID, self.TARGET_JID, owner=self.MEMBER_JID, owner_admin=True
        )
        data = GroupCommandDataFactory.build(
            text=',ban', sender_jid=self.MEMBER_JID, mentioned_jids=[self.TARGET_JID]
        )

        await command.run(data)

        mock_whatsapp.group_participants_update.assert_called_once()


class TestNobodyLeftToBan:
    BOT_JID = '5500000000000@s.whatsapp.net'
    OWNER_JID = '5511999990099@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_says_so_when_only_the_bot_and_the_owner_are_left(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, self.OWNER_JID, owner=self.OWNER_JID, owner_admin=True
        )
        data = GroupCommandDataFactory.build(text=',ban', is_admin=True)

        messages = await command.run(data)

        assert messages[0].content.text == 'Não sobrou ninguém pra eu banir! 🤷'
        mock_whatsapp.group_participants_update.assert_not_called()


class TestMentionedBans:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'
    OWNER_JID = '5511999990099@s.whatsapp.net'
    FIRST_JID = '5511999990001@s.whatsapp.net'
    SECOND_JID = '5511999990002@s.whatsapp.net'

    def admin_bans(self, *mentioned: str):
        return GroupCommandDataFactory.build(
            is_admin=True, text=',ban', jid=self.CHAT_JID, mentioned_jids=list(mentioned)
        )

    @pytest.mark.anyio
    async def test_reads_the_metadata_of_the_chat(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(self.BOT_JID)

        await command.run(self.admin_bans(self.FIRST_JID))

        mock_whatsapp.group_metadata.assert_awaited_once_with(self.CHAT_JID)

    @pytest.mark.anyio
    async def test_a_bot_missing_from_the_group_is_not_admin(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(self.FIRST_JID)

        messages = await command.run(self.admin_bans(self.FIRST_JID))

        assert messages[0].content.text == BanCommand.BOT_NOT_ADMIN_MSG

    @pytest.mark.anyio
    async def test_removes_each_mentioned_member_from_the_chat(
        self, command, mock_whatsapp, mocker
    ):
        mock_whatsapp.group_metadata.return_value = make_group_participants(self.BOT_JID)

        await command.run(self.admin_bans(self.FIRST_JID, self.SECOND_JID))

        assert mock_whatsapp.group_participants_update.await_args_list == [
            mocker.call(self.CHAT_JID, [self.FIRST_JID], 'remove'),
            mocker.call(self.CHAT_JID, [self.SECOND_JID], 'remove'),
        ]

    @pytest.mark.anyio
    @pytest.mark.parametrize('spared', [BOT_JID, OWNER_JID])
    async def test_sparing_the_bot_or_the_admin_owner_still_bans_the_rest(
        self, command, mock_whatsapp, spared
    ):
        mock_whatsapp.group_metadata.return_value = make_group_participants(
            self.BOT_JID, self.OWNER_JID, owner=self.OWNER_JID, owner_admin=True
        )

        await command.run(self.admin_bans(spared, self.FIRST_JID))

        mock_whatsapp.group_participants_update.assert_awaited_once_with(
            self.CHAT_JID, [self.FIRST_JID], 'remove'
        )

    @pytest.mark.anyio
    async def test_a_failed_removal_logs_it_and_moves_on(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = make_group_participants(self.BOT_JID)
        mock_whatsapp.group_participants_update.side_effect = [RuntimeError('not allowed'), []]

        with capture_logs() as logs:
            messages = await command.run(self.admin_bans(self.FIRST_JID, self.SECOND_JID))

        assert [m.content.mentions for m in messages] == [[self.SECOND_JID]]
        assert [
            (log['event'], log['jid'], log['target']) for log in logs if log['log_level'] == 'error'
        ] == [('ban_mentioned_error', self.CHAT_JID, self.FIRST_JID)]
