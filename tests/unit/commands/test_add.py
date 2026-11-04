import pytest
from structlog.testing import capture_logs

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
        data = GroupCommandDataFactory.build(is_admin=True, text=',add', jid=self.CHAT_JID)

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
        data = GroupCommandDataFactory.build(
            is_admin=True, text=',add 00999990000', jid=self.CHAT_JID
        )

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
        data = GroupCommandDataFactory.build(
            is_admin=True, text=',add 11999990000123', jid=self.CHAT_JID
        )

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
        data = GroupCommandDataFactory.build(
            is_admin=True, text=',add 11999990000', jid=self.CHAT_JID
        )

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
        data = GroupCommandDataFactory.build(
            is_admin=True, text=',add 11999990000', jid=self.CHAT_JID
        )

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
        data = GroupCommandDataFactory.build(
            is_admin=True, text=',add 11999990000', jid=self.CHAT_JID
        )

        messages = await command.run(data)

        assert any('não consegui' in m.content.text for m in messages)


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
        data = GroupCommandDataFactory.build(is_admin=True, text=',add', jid=self.CHAT_JID)

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
        data = GroupCommandDataFactory.build(is_admin=True, text=',add', jid=self.CHAT_JID)

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
        data = GroupCommandDataFactory.build(is_admin=True, text=',add', jid=self.CHAT_JID)

        messages = await command.run(data)

        assert any('não consegui' in m.content.text for m in messages)


class TestAdminOnly:
    BOT_JID = '5500000000000@s.whatsapp.net'
    MEMBER_JID = '5511999990001@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_a_member_is_refused(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [
                {'id': self.BOT_JID, 'admin': 'admin'},
                {'id': self.MEMBER_JID, 'admin': None},
            ],
        }
        data = GroupCommandDataFactory.build(text=',add 11999990000', sender_jid=self.MEMBER_JID)

        messages = await command.run(data)

        assert messages[0].content.text == 'Só admin pode usar esse comando. 🙅'
        mock_whatsapp.on_whatsapp.assert_not_called()


BOT_JID = '5500000000000@s.whatsapp.net'
CHAT_JID = '120363044041082732@g.us'
FOUND_JID = '5527955555555@s.whatsapp.net'


@pytest.fixture
def bot_is_admin(mock_whatsapp):
    mock_whatsapp.group_metadata.return_value = {
        'participants': [{'id': BOT_JID, 'admin': 'admin'}]
    }
    mock_whatsapp.on_whatsapp.return_value = [{'exists': True, 'jid': FOUND_JID}]
    return mock_whatsapp


@pytest.fixture
def rng(mocker):
    return mocker.patch('bot.domain.commands.add.random')


def admin_says(text: str):
    return GroupCommandDataFactory.build(is_admin=True, text=text, jid=CHAT_JID)


def error_logs(logs: list[dict]) -> list[tuple]:
    return [(log['event'], log['jid'], log['phone']) for log in logs if log['log_level'] == 'error']


class TestGroupLookup:
    @pytest.mark.anyio
    async def test_reads_the_metadata_of_the_chat(self, command, bot_is_admin):
        await command.run(admin_says(',add 27999990000'))

        bot_is_admin.group_metadata.assert_awaited_once_with(CHAT_JID)

    @pytest.mark.anyio
    async def test_a_bot_missing_from_the_group_is_not_admin(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {'participants': []}

        messages = await command.run(admin_says(',add 27999990000'))

        assert messages[0].content.text == AddCommand.BOT_NOT_ADMIN_MSG


class TestRandomNumber:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('area_code', 'number'),
        [('27', '27955555555'), ('31', '3185555555')],
    )
    async def test_builds_the_number_from_the_area_code_prefix_and_digits(
        self, command, bot_is_admin, rng, area_code, number
    ):
        rng.choice.side_effect = [area_code, len(number)]
        rng.randint.return_value = 5

        await command.run(admin_says(',add'))

        bot_is_admin.on_whatsapp.assert_awaited_once_with([f'55{number}'])

    @pytest.mark.anyio
    async def test_draws_the_size_and_each_digit_from_the_valid_ranges(
        self, command, bot_is_admin, rng, mocker
    ):
        rng.choice.side_effect = ['27', 10]
        rng.randint.return_value = 0

        await command.run(admin_says(',add'))

        assert rng.choice.call_args_list[1] == mocker.call([10, 11])
        assert rng.randint.call_args_list == [mocker.call(0, 9)] * 7

    @pytest.mark.anyio
    async def test_adds_the_number_found(self, command, bot_is_admin, rng):
        rng.choice.side_effect = ['27', 11]
        rng.randint.return_value = 5

        await command.run(admin_says(',add'))

        bot_is_admin.group_participants_update.assert_awaited_once_with(
            CHAT_JID, [FOUND_JID], 'add'
        )

    @pytest.mark.anyio
    async def test_a_failed_add_logs_the_chat_and_the_number(self, command, bot_is_admin, rng):
        rng.choice.side_effect = ['27', 11]
        rng.randint.return_value = 5
        bot_is_admin.group_participants_update.side_effect = RuntimeError('not allowed')

        with capture_logs() as logs:
            messages = await command.run(admin_says(',add'))

        assert messages[0].content.text == 'Ops, não consegui adicionar o número 27955555555 😅'
        assert error_logs(logs) == [('add_random_phone_error', CHAT_JID, '27955555555')]


class TestGivenNumber:
    @pytest.mark.anyio
    async def test_looks_the_number_up_with_the_country_code(self, command, bot_is_admin):
        await command.run(admin_says(',add 27999990000'))

        bot_is_admin.on_whatsapp.assert_awaited_once_with(['5527999990000'])

    @pytest.mark.anyio
    async def test_a_failed_add_logs_the_chat_and_the_number(self, command, bot_is_admin):
        bot_is_admin.group_participants_update.side_effect = RuntimeError('not allowed')

        with capture_logs() as logs:
            await command.run(admin_says(',add 27999990000'))

        assert error_logs(logs) == [('add_phone_error', CHAT_JID, '27999990000')]
