import pytest

from bot.domain.commands.group_mentions import GroupMentionsCommand
from bot.domain.services.group_mentions import GroupMentionsService
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

CHAT_JID = '120363044041082732@g.us'
SENDER_JID = '5511999990000@s.whatsapp.net'


@pytest.fixture
def mock_service(mocker):
    return mocker.AsyncMock(spec=GroupMentionsService)


@pytest.fixture
def command(mock_service):
    return GroupMentionsCommand(service=mock_service)


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',grupo', True),
            (', grupo', True),
            (', GRUPO', True),
            (', grupo create test', True),
            (', grupo list', True),
            (', grupo devs', True),
            ('grupo', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestGroupOnly:
    @pytest.mark.anyio
    async def test_rejects_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=',grupo list')

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'só funciona em grupo' in messages[0].content.text


class TestCreate:
    @pytest.mark.anyio
    async def test_create_success(self, command, mock_service):
        mock_service.create.return_value = {'ok': True, 'group_name': 'devs'}
        data = GroupCommandDataFactory.build(
            text=',grupo create devs',
            jid=CHAT_JID,
            sender_jid=SENDER_JID,
        )

        messages = await command.run(data)

        assert 'devs' in messages[0].content.text
        assert 'criado com sucesso' in messages[0].content.text

    @pytest.mark.anyio
    async def test_create_duplicate(self, command, mock_service):
        mock_service.create.return_value = {
            'ok': False,
            'message': 'Já existe um grupo com o nome *devs* 😔',
        }
        data = GroupCommandDataFactory.build(text=',grupo create devs', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Já existe' in messages[0].content.text

    @pytest.mark.anyio
    async def test_create_no_name(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=',grupo create', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Cadê o nome' in messages[0].content.text
        mock_service.create.assert_not_called()

    @pytest.mark.anyio
    async def test_create_name_too_long(self, command, mock_service):
        data = GroupCommandDataFactory.build(
            text=',grupo create nomemuuuuiiitolongo',
            jid=CHAT_JID,
        )

        messages = await command.run(data)

        assert 'tamanho' in messages[0].content.text
        mock_service.create.assert_not_called()

    @pytest.mark.anyio
    async def test_create_reserved_name(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=',grupo create list', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'comando' in messages[0].content.text
        mock_service.create.assert_not_called()

    @pytest.mark.anyio
    async def test_create_name_with_space(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=',grupo create dev ops', jid=CHAT_JID)

        messages = await command.run(data)

        # "dev ops" contains space -> validation error
        assert 'espaço' in messages[0].content.text


class TestRename:
    @pytest.mark.anyio
    async def test_rename_success(self, command, mock_service):
        mock_service.rename.return_value = {
            'ok': True,
            'old_name': 'devs',
            'new_name': 'eng',
        }
        data = GroupCommandDataFactory.build(text=',grupo rename devs eng', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'renomeado' in messages[0].content.text
        assert 'devs' in messages[0].content.text
        assert 'eng' in messages[0].content.text

    @pytest.mark.anyio
    async def test_rename_missing_names(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=',grupo rename devs', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Cadê os nomes' in messages[0].content.text


class TestDelete:
    @pytest.mark.anyio
    async def test_delete_success(self, command, mock_service):
        mock_service.delete.return_value = {'ok': True, 'group_name': 'devs'}
        data = GroupCommandDataFactory.build(text=',grupo delete devs', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'deletado com sucesso' in messages[0].content.text

    @pytest.mark.anyio
    async def test_delete_no_name(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=',grupo delete', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Cadê o nome' in messages[0].content.text

    @pytest.mark.anyio
    async def test_delete_not_found(self, command, mock_service):
        mock_service.delete.return_value = {
            'ok': False,
            'message': 'Não existe um grupo com o nome *devs* 😔',
        }
        data = GroupCommandDataFactory.build(text=',grupo delete devs', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Não existe' in messages[0].content.text


class TestList:
    @pytest.mark.anyio
    async def test_list_all(self, command, mock_service):
        mock_service.list_all.return_value = {
            'ok': True,
            'groups': [{'name': 'devs'}, {'name': 'design'}],
        }
        data = GroupCommandDataFactory.build(text=',grupo list', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'GRUPOS' in messages[0].content.text
        assert 'devs' in messages[0].content.text
        assert 'design' in messages[0].content.text

    @pytest.mark.anyio
    async def test_list_all_empty(self, command, mock_service):
        mock_service.list_all.return_value = {
            'ok': False,
            'message': 'Você não tem grupos 😔',
        }
        data = GroupCommandDataFactory.build(text=',grupo list', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'não tem grupos' in messages[0].content.text

    @pytest.mark.anyio
    async def test_list_one(self, command, mock_service):
        mock_service.list_one.return_value = {
            'ok': True,
            'name': 'devs',
            'participants': ['5511999990000@s.whatsapp.net', '5511999990001@s.whatsapp.net'],
        }
        data = GroupCommandDataFactory.build(text=',grupo list devs', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'DEVS' in messages[0].content.text
        assert '@5511999990000' in messages[0].content.text
        assert messages[0].content.mentions is not None


class TestAdd:
    @pytest.mark.anyio
    async def test_add_self(self, command, mock_service):
        mock_service.add.return_value = {
            'ok': True,
            'group_name': 'devs',
            'self_only': True,
        }
        data = GroupCommandDataFactory.build(
            text=',grupo add devs',
            jid=CHAT_JID,
            sender_jid=SENDER_JID,
        )

        messages = await command.run(data)

        assert 'Você foi adicionado' in messages[0].content.text

    @pytest.mark.anyio
    async def test_add_others(self, command, mock_service):
        mock_service.add.return_value = {
            'ok': True,
            'group_name': 'devs',
            'self_only': False,
        }
        data = GroupCommandDataFactory.build(
            text=',grupo add devs @5511999990001',
            jid=CHAT_JID,
            sender_jid=SENDER_JID,
            mentioned_jids=['5511999990001@s.whatsapp.net'],
        )

        messages = await command.run(data)

        assert 'Participantes adicionados' in messages[0].content.text

    @pytest.mark.anyio
    async def test_add_no_name(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=',grupo add', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Cadê o nome' in messages[0].content.text


class TestExit:
    @pytest.mark.anyio
    async def test_exit_self(self, command, mock_service):
        mock_service.exit.return_value = {
            'ok': True,
            'group_name': 'devs',
            'self_only': True,
        }
        data = GroupCommandDataFactory.build(
            text=',grupo exit devs',
            jid=CHAT_JID,
            sender_jid=SENDER_JID,
        )

        messages = await command.run(data)

        assert 'Você foi removido' in messages[0].content.text

    @pytest.mark.anyio
    async def test_exit_by_indices(self, command, mock_service):
        mock_service.exit.return_value = {
            'ok': True,
            'group_name': 'devs',
            'self_only': False,
        }
        data = GroupCommandDataFactory.build(
            text=',grupo exit devs 1 3',
            jid=CHAT_JID,
            sender_jid=SENDER_JID,
        )

        messages = await command.run(data)

        assert 'Participantes removidos' in messages[0].content.text
        mock_service.exit.assert_called_once()
        call_args = mock_service.exit.call_args
        assert call_args[0][3] == [1, 3]  # indices

    @pytest.mark.anyio
    async def test_exit_no_name(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=',grupo exit', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Cadê o nome' in messages[0].content.text


class TestMention:
    @pytest.mark.anyio
    async def test_mention_group(self, command, mock_service):
        mock_service.mention.return_value = {
            'ok': True,
            'participants': ['5511999990000@s.whatsapp.net', '5511999990001@s.whatsapp.net'],
        }
        data = GroupCommandDataFactory.build(text=',grupo devs', jid=CHAT_JID)

        messages = await command.run(data)

        assert '@5511999990000' in messages[0].content.text
        assert '@5511999990001' in messages[0].content.text
        assert messages[0].content.mentions is not None

    @pytest.mark.anyio
    async def test_mention_with_text(self, command, mock_service):
        mock_service.mention.return_value = {
            'ok': True,
            'participants': ['5511999990000@s.whatsapp.net'],
        }
        data = GroupCommandDataFactory.build(text=',grupo devs ola galera', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'ola galera' in messages[0].content.text
        assert '@5511999990000' in messages[0].content.text

    @pytest.mark.anyio
    async def test_mention_not_found(self, command, mock_service):
        mock_service.mention.return_value = {
            'ok': False,
            'message': 'Não existe um grupo com o nome *xpto* 😔',
        }
        data = GroupCommandDataFactory.build(text=',grupo xpto', jid=CHAT_JID)

        messages = await command.run(data)

        assert 'Não existe' in messages[0].content.text


class TestStripJid:
    @pytest.mark.parametrize(
        ('jid', 'expected'),
        [
            ('5511999990000@s.whatsapp.net', '5511999990000'),
            ('5511999990000@lid', '5511999990000'),
            ('5511999990000', '5511999990000'),
        ],
    )
    def test_strip_jid(self, jid, expected):
        from bot.domain.jid import strip_jid

        assert strip_jid(jid) == expected
