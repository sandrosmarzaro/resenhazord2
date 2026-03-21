import pytest

from bot.domain.commands.dev import DevCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def mock_service(mocker):
    return mocker.AsyncMock()


@pytest.fixture
def command(mock_service):
    return DevCommand(service=mock_service)


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', dev', True),
            (',dev', True),
            (', DEV', True),
            (', dev add', True),
            (', dev remove', True),
            ('  , dev  ', True),
            ('dev', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestList:
    @pytest.mark.anyio
    async def test_list_devs(self, command, mock_service):
        mock_service.list_all.return_value = ['5511999@s.whatsapp.net', '5522888@s.whatsapp.net']
        data = GroupCommandDataFactory.build(text=', dev')

        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'Devs' in messages[0].content.text
        assert '5511999' in messages[0].content.text
        assert '5522888' in messages[0].content.text

    @pytest.mark.anyio
    async def test_list_empty(self, command, mock_service):
        mock_service.list_all.return_value = []
        data = GroupCommandDataFactory.build(text=', dev')

        messages = await command.run(data)

        assert 'Nenhum dev' in messages[0].content.text


class TestAdd:
    @pytest.mark.anyio
    async def test_add_mentioned_user(self, command, mock_service):
        mock_service.add.return_value = True
        data = GroupCommandDataFactory.build(
            text=', dev add @5511999',
            mentioned_jids=['5511999@s.whatsapp.net'],
        )

        messages = await command.run(data)

        mock_service.add.assert_called_once_with('5511999@s.whatsapp.net')
        assert 'adicionado' in messages[0].content.text

    @pytest.mark.anyio
    async def test_add_already_dev(self, command, mock_service):
        mock_service.add.return_value = False
        data = GroupCommandDataFactory.build(
            text=', dev add @5511999',
            mentioned_jids=['5511999@s.whatsapp.net'],
        )

        messages = await command.run(data)

        assert 'já é dev' in messages[0].content.text

    @pytest.mark.anyio
    async def test_add_no_mention(self, command, mock_service):
        data = GroupCommandDataFactory.build(text=', dev add')

        messages = await command.run(data)

        assert 'Uso:' in messages[0].content.text


class TestRemove:
    @pytest.mark.anyio
    async def test_remove_mentioned_user(self, command, mock_service):
        mock_service.remove.return_value = True
        data = GroupCommandDataFactory.build(
            text=', dev remove @5511999',
            mentioned_jids=['5511999@s.whatsapp.net'],
        )

        messages = await command.run(data)

        mock_service.remove.assert_called_once_with('5511999@s.whatsapp.net')
        assert 'removido' in messages[0].content.text

    @pytest.mark.anyio
    async def test_remove_not_dev(self, command, mock_service):
        mock_service.remove.return_value = False
        data = GroupCommandDataFactory.build(
            text=', dev remove @5511999',
            mentioned_jids=['5511999@s.whatsapp.net'],
        )

        messages = await command.run(data)

        assert 'não é dev' in messages[0].content.text
