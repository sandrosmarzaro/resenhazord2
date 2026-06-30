import pytest

from bot.application.config_service import ConfigService
from bot.domain.commands.base import CommandConfig, CommandScope
from bot.domain.models.chat_config import ChatConfig, ChatPolicy
from tests.factories.command_data import GroupCommandDataFactory


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
