import pytest

from bot.application.config_service import ConfigService
from bot.domain.commands.base import CommandConfig, CommandScope
from bot.domain.models.blocked_member import BlockedMember
from bot.domain.models.chat_config import ChatConfig, ChatPolicy
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

PN = '5527900000003@s.whatsapp.net'
LID = '123456789012345@lid'


@pytest.fixture
def data():
    return GroupCommandDataFactory(platform='whatsapp')


def public(name: str = 'oi') -> CommandConfig:
    return CommandConfig(name=name, scope=CommandScope.PUBLIC)


def nsfw(name: str = 'hentai') -> CommandConfig:
    return CommandConfig(name=name, scope=CommandScope.NSFW)


class TestNonTogglable:
    @pytest.mark.anyio
    async def test_locked_scope_is_always_enabled_without_loading(self, mocker, data):
        store = mocker.AsyncMock()
        service = ConfigService(store)

        enabled = await service.is_enabled(data, CommandConfig(name='dev', scope=CommandScope.DEV))

        assert enabled is True
        store.load.assert_not_called()


class TestOpenPolicy:
    @pytest.mark.anyio
    async def test_public_command_defaults_on(self, mocker, data):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(policy=ChatPolicy.OPEN)
        service = ConfigService(store)

        enabled = await service.is_enabled(data, public())

        assert enabled is True
        store.load.assert_awaited_once_with('whatsapp', data.jid)

    @pytest.mark.anyio
    async def test_nsfw_command_defaults_off(self, mocker, data):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(policy=ChatPolicy.OPEN)
        service = ConfigService(store)

        enabled = await service.is_enabled(data, nsfw())

        assert enabled is False


class TestOverride:
    @pytest.mark.anyio
    async def test_override_enables_nsfw(self, mocker, data):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(policy=ChatPolicy.OPEN, overrides={'hentai': True})
        service = ConfigService(store)

        enabled = await service.is_enabled(data, nsfw())

        assert enabled is True

    @pytest.mark.anyio
    async def test_override_disables_public(self, mocker, data):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(policy=ChatPolicy.OPEN, overrides={'oi': False})
        service = ConfigService(store)

        enabled = await service.is_enabled(data, public())

        assert enabled is False


class TestCuratedPolicy:
    @pytest.mark.anyio
    async def test_public_command_off_without_override(self, mocker, data):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(policy=ChatPolicy.CURATED)
        service = ConfigService(store)

        enabled = await service.is_enabled(data, public())

        assert enabled is False

    @pytest.mark.anyio
    async def test_override_is_the_allow_list(self, mocker, data):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(policy=ChatPolicy.CURATED, overrides={'oi': True})
        service = ConfigService(store)

        enabled = await service.is_enabled(data, public())

        assert enabled is True


class TestIsBlocked:
    @pytest.mark.anyio
    async def test_a_group_blocks_a_sender_stored_under_the_other_form(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(blocked=(BlockedMember(key=PN, alt_key=LID),))
        data = GroupCommandDataFactory(platform='whatsapp', sender_jid=LID, participant=LID)

        blocked = await ConfigService(store).is_blocked(data)

        assert blocked is True
        store.load.assert_awaited_once_with('whatsapp', data.jid)

    @pytest.mark.anyio
    async def test_a_group_lets_an_unblocked_sender_through(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig(blocked=(BlockedMember(key=PN, alt_key=LID),))
        data = GroupCommandDataFactory(platform='whatsapp')

        assert await ConfigService(store).is_blocked(data) is False

    @pytest.mark.anyio
    async def test_a_private_chat_never_blocks_without_loading(self, mocker):
        store = mocker.AsyncMock()
        data = PrivateCommandDataFactory(platform='whatsapp')

        blocked = await ConfigService(store).is_blocked(data)

        assert blocked is False
        store.load.assert_not_called()
