import pytest

from bot.domain.commands.config import ConfigCommand
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def admin(mocker):
    admin = mocker.AsyncMock()
    admin.is_authorized.return_value = True
    return admin


@pytest.fixture
def editor(mocker):
    editor = mocker.AsyncMock()
    editor.apply.return_value = 'feito'
    return editor


@pytest.fixture
def command(admin, editor):
    return ConfigCommand(admin=admin, editor=editor)


class TestAuthorized:
    @pytest.mark.anyio
    async def test_delegates_rest_to_editor(self, command, editor):
        data = GroupCommandDataFactory(text=', config on hentai', platform='whatsapp')

        result = await command.run(data)

        assert result[0].content.text == 'feito'
        editor.apply.assert_awaited_once()
        assert editor.apply.await_args.args[1] == 'on hentai'

    @pytest.mark.anyio
    async def test_checks_admin_with_injected_port(self, command, admin):
        data = GroupCommandDataFactory(text=', config', platform='whatsapp')

        await command.run(data)

        admin.is_authorized.assert_awaited_once()
        assert admin.is_authorized.await_args.args[0] is data


class TestUnauthorized:
    @pytest.mark.anyio
    async def test_non_admin_is_blocked_before_editor(self, command, admin, editor):
        admin.is_authorized.return_value = False
        data = GroupCommandDataFactory(text=', config off oi', platform='whatsapp')

        result = await command.run(data)

        assert 'admin' in result[0].content.text.lower()
        editor.apply.assert_not_called()
