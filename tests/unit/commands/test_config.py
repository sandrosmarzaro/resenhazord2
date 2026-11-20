import pytest

from bot.domain.builders.reply import Reply
from bot.domain.commands.config import ConfigCommand
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def admin(mocker):
    admin = mocker.AsyncMock()
    admin.is_authorized.return_value = True
    admin.is_admin.return_value = True
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


class TestDevAdminToggle:
    @pytest.mark.anyio
    async def test_turning_it_on_takes_a_real_admin(self, command, admin, editor):
        admin.is_admin.return_value = False
        data = GroupCommandDataFactory(text=', config dev on', platform='whatsapp')

        result = await command.run(data)

        assert 'admin' in result[0].content.text.lower()
        editor.apply.assert_not_called()

    @pytest.mark.anyio
    async def test_a_real_admin_turns_it_on(self, command, admin, editor):
        data = GroupCommandDataFactory(text=', config Dev On', platform='whatsapp')

        await command.run(data)

        admin.is_admin.assert_awaited_once()
        admin.is_authorized.assert_not_called()
        assert editor.apply.await_args.args[1] == 'Dev On'

    @pytest.mark.anyio
    async def test_turning_it_off_takes_the_usual_check(self, command, admin, editor):
        data = GroupCommandDataFactory(text=', config dev off', platform='whatsapp')

        await command.run(data)

        admin.is_authorized.assert_awaited_once()
        admin.is_admin.assert_not_called()
        assert editor.apply.await_args.args[1] == 'dev off'


class TestMemberBlocks:
    @pytest.fixture
    def blocks(self, mocker):
        blocks = mocker.AsyncMock()
        blocks.apply.return_value = Reply.to(GroupCommandDataFactory()).text('bloqueado')
        return blocks

    @pytest.mark.anyio
    async def test_hands_the_verb_and_port_to_member_blocks(
        self, admin, editor, blocks, mock_whatsapp
    ):
        command = ConfigCommand(admin=admin, editor=editor, blocks=blocks, whatsapp=mock_whatsapp)
        data = GroupCommandDataFactory(text=', config Bloquear @fulano', platform='whatsapp')

        result = await command.run(data)

        blocks.apply.assert_awaited_once_with(data, 'bloquear', mock_whatsapp)
        assert result[0].content.text == 'bloqueado'
        editor.apply.assert_not_called()

    @pytest.mark.anyio
    async def test_an_unauthorized_member_cannot_block(self, admin, editor, blocks):
        admin.is_authorized.return_value = False
        command = ConfigCommand(admin=admin, editor=editor, blocks=blocks)
        data = GroupCommandDataFactory(text=', config bloquear @fulano', platform='whatsapp')

        await command.run(data)

        blocks.apply.assert_not_called()
