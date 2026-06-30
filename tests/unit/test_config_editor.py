import pytest

from bot.application.command_registry import CommandRegistry
from bot.application.config_editor import ConfigEditor
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    CommandScope,
    ParsedCommand,
)
from bot.domain.models.chat_config import ChatConfig, ChatPolicy
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from tests.factories.command_data import GroupCommandDataFactory


class _Fake(Command):
    def __init__(self, name: str, scope: CommandScope, category: Category | None) -> None:
        super().__init__()
        self._cfg = CommandConfig(name=name, scope=scope, category=category)

    @property
    def config(self) -> CommandConfig:
        return self._cfg

    @property
    def menu_description(self) -> str:
        return ''

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return []


@pytest.fixture
def registry():
    registry = CommandRegistry.instance()
    registry.register(_Fake('oi', CommandScope.PUBLIC, Category.RANDOM))
    registry.register(_Fake('hentai', CommandScope.NSFW, Category.OTHER))
    registry.register(_Fake('porno', CommandScope.NSFW, Category.OTHER))
    registry.register(_Fake('download', CommandScope.PUBLIC, Category.DOWNLOAD))
    registry.register(_Fake('dev', CommandScope.DEV, None))
    return registry


@pytest.fixture
def store(mocker):
    store = mocker.AsyncMock()
    store.load.return_value = ChatConfig()
    return store


@pytest.fixture
def editor(store, registry):
    return ConfigEditor(store=store, registry=registry)


@pytest.fixture
def data():
    return GroupCommandDataFactory(platform='whatsapp')


class TestEnableDisable:
    @pytest.mark.anyio
    async def test_enable_single_command(self, editor, store, data):
        response = await editor.apply(data, 'on hentai')

        assert 'hentai' in response
        store.set_override.assert_awaited_once()
        call = store.set_override.await_args
        assert call.args[1] == 'hentai'
        assert call.kwargs['enabled'] is True

    @pytest.mark.anyio
    async def test_disable_single_command(self, editor, store, data):
        await editor.apply(data, 'off oi')

        assert store.set_override.await_args.kwargs['enabled'] is False


class TestSubtypeBatch:
    @pytest.mark.anyio
    async def test_nsfw_subtype_targets_all_nsfw_commands(self, editor, store, data):
        await editor.apply(data, 'on nsfw')

        toggled = {call.args[1] for call in store.set_override.await_args_list}
        assert toggled == {'hentai', 'porno'}

    @pytest.mark.anyio
    async def test_category_subtype_targets_that_category(self, editor, store, data):
        await editor.apply(data, 'off download')

        toggled = {call.args[1] for call in store.set_override.await_args_list}
        assert toggled == {'download'}


class TestInvalidTarget:
    @pytest.mark.anyio
    async def test_unknown_token_writes_nothing(self, editor, store, data):
        response = await editor.apply(data, 'on nonsense')

        assert 'não reconheço' in response.lower()
        store.set_override.assert_not_called()

    @pytest.mark.anyio
    async def test_non_togglable_command_is_rejected(self, editor, store, data):
        response = await editor.apply(data, 'on dev')

        assert 'não reconheço' in response.lower()
        store.set_override.assert_not_called()


class TestReset:
    @pytest.mark.anyio
    async def test_reset_clears_override(self, editor, store, data):
        await editor.apply(data, 'reset hentai')

        store.clear_override.assert_awaited_once()
        assert store.clear_override.await_args.args[1] == 'hentai'

    @pytest.mark.anyio
    async def test_reset_unknown_token_clears_nothing(self, editor, store, data):
        response = await editor.apply(data, 'reset nonsense')

        assert 'não reconheço' in response.lower()
        store.clear_override.assert_not_called()


class TestUnknownVerb:
    @pytest.mark.anyio
    async def test_unknown_verb_returns_help(self, editor, store, data):
        response = await editor.apply(data, 'frobnicate hentai')

        assert 'use:' in response.lower()
        store.set_override.assert_not_called()


class TestPolicy:
    @pytest.mark.anyio
    async def test_sets_curated(self, editor, store, data):
        response = await editor.apply(data, 'policy curated')

        store.set_policy.assert_awaited_once()
        assert store.set_policy.await_args.args[1] is ChatPolicy.CURATED
        assert 'curated' in response

    @pytest.mark.anyio
    async def test_rejects_unknown_policy(self, editor, store, data):
        await editor.apply(data, 'policy bogus')

        store.set_policy.assert_not_called()


class TestRender:
    @pytest.mark.anyio
    async def test_empty_renders_status(self, editor, store, data):
        store.load.return_value = ChatConfig(
            policy=ChatPolicy.CURATED, overrides={'oi': True, 'hentai': False}
        )

        response = await editor.apply(data, '')

        assert 'curated' in response
        assert 'oi' in response
        assert 'hentai' in response
