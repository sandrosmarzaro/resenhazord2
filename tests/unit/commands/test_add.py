import pytest

from bot.domain.commands.add import AddCommand
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command(mock_whatsapp):
    return AddCommand(bot_jid='5500000000000@s.whatsapp.net', whatsapp=mock_whatsapp)


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',add', True),
            (', add', True),
            (', ADD', True),
            (', add 11999990000', True),
            ('add', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestGroupOnly:
    @pytest.mark.anyio
    async def test_rejects_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=',add')
        messages = await command.run(data)

        assert 'só funciona em grupo' in messages[0].content.text


class TestBotNotAdmin:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'

    @pytest.mark.anyio
    async def test_bot_not_admin(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': None}],
        }
        data = GroupCommandDataFactory.build(text=',add', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert 'não sou admin' in messages[0].content.text


class TestInvalidDDD:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'

    @pytest.mark.anyio
    async def test_invalid_ddd(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        data = GroupCommandDataFactory.build(text=',add 00999990000', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert 'DDD' in messages[0].content.text


class TestPhoneTooLong:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'

    @pytest.mark.anyio
    async def test_phone_too_long_warning(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        mock_whatsapp.on_whatsapp.return_value = [
            {'exists': True, 'jid': '5511999990000123@s.whatsapp.net'},
        ]
        data = GroupCommandDataFactory.build(text=',add 11999990000123', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert any('tamanho' in m.content.text for m in messages)


class TestAddSpecificPhone:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'

    @pytest.mark.anyio
    async def test_add_existing_phone(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        mock_whatsapp.on_whatsapp.return_value = [
            {'exists': True, 'jid': '5511999990000@s.whatsapp.net'},
        ]
        data = GroupCommandDataFactory.build(text=',add 11999990000', jid=self.CHAT_JID)

        messages = await command.run(data)

        # No error messages = success
        assert len(messages) == 0
        mock_whatsapp.group_participants_update.assert_called_once_with(
            self.CHAT_JID, ['5511999990000@s.whatsapp.net'], 'add'
        )

    @pytest.mark.anyio
    async def test_add_nonexistent_phone_uses_lid(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        mock_whatsapp.on_whatsapp.return_value = [{'exists': False}]
        data = GroupCommandDataFactory.build(text=',add 11999990000', jid=self.CHAT_JID)

        await command.run(data)

        mock_whatsapp.group_participants_update.assert_called_once_with(
            self.CHAT_JID, ['5511999990000@lid'], 'add'
        )

    @pytest.mark.anyio
    async def test_add_phone_error(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        mock_whatsapp.on_whatsapp.return_value = [
            {'exists': True, 'jid': '5511999990000@s.whatsapp.net'},
        ]
        mock_whatsapp.group_participants_update.side_effect = Exception('API error')
        data = GroupCommandDataFactory.build(text=',add 11999990000', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert any('Não consegui' in m.content.text for m in messages)


class TestAddRandomPhone:
    BOT_JID = '5500000000000@s.whatsapp.net'
    CHAT_JID = '120363044041082732@g.us'

    @pytest.mark.anyio
    async def test_add_random_success(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        mock_whatsapp.on_whatsapp.return_value = [
            {'exists': True, 'jid': '5511999990000@s.whatsapp.net'},
        ]
        data = GroupCommandDataFactory.build(text=',add', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert len(messages) == 0
        mock_whatsapp.group_participants_update.assert_called_once()

    @pytest.mark.anyio
    async def test_add_random_retries_until_found(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        mock_whatsapp.on_whatsapp.side_effect = [
            [{'exists': False}],
            [{'exists': False}],
            [{'exists': True, 'jid': '5521999990000@s.whatsapp.net'}],
        ]
        data = GroupCommandDataFactory.build(text=',add', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert len(messages) == 0
        assert mock_whatsapp.on_whatsapp.call_count == 3
        mock_whatsapp.group_participants_update.assert_called_once()

    @pytest.mark.anyio
    async def test_add_random_error(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [{'id': self.BOT_JID, 'admin': 'admin'}],
        }
        mock_whatsapp.on_whatsapp.return_value = [
            {'exists': True, 'jid': '5511999990000@s.whatsapp.net'},
        ]
        mock_whatsapp.group_participants_update.side_effect = Exception('API error')
        data = GroupCommandDataFactory.build(text=',add', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert any('Não consegui' in m.content.text for m in messages)
