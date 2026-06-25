import pytest

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    CommandScope,
    ParsedCommand,
)
from bot.domain.models.chat_config import ChatKey, ChatPolicy, ChatType
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from scripts.seed_config import _nsfw_command_names, _parse_chat_ids, seed


class _Fake(Command):
    def __init__(self, name: str, scope: CommandScope) -> None:
        super().__init__()
        self._cfg = CommandConfig(name=name, scope=scope, category=Category.RANDOM)

    @property
    def config(self) -> CommandConfig:
        return self._cfg

    @property
    def menu_description(self) -> str:
        return ''

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return []


class TestSeedTelegram:
    @pytest.mark.anyio
    async def test_enables_each_nsfw_command_per_chat(self, mocker):
        store = mocker.AsyncMock()

        await seed(store, ['porno', 'hentai'], [-100, -200], '')

        assert store.set_override.await_count == 4
        calls = store.set_override.await_args_list
        assert ChatKey('telegram', '-100', ChatType.GROUP) == calls[0].args[0]
        assert all(call.kwargs['enabled'] is True for call in calls)
        store.set_policy.assert_not_called()


class TestSeedResenha:
    @pytest.mark.anyio
    async def test_marks_resenha_curated(self, mocker):
        store = mocker.AsyncMock()

        await seed(store, [], [], '123@g.us')

        store.set_policy.assert_awaited_once_with(
            ChatKey('whatsapp', '123@g.us', ChatType.GROUP), ChatPolicy.CURATED
        )

    @pytest.mark.anyio
    async def test_empty_resenha_skips_policy(self, mocker):
        store = mocker.AsyncMock()

        await seed(store, ['porno'], [], '')

        store.set_policy.assert_not_called()


class TestHelpers:
    def test_parse_chat_ids_trims_and_casts(self):
        assert _parse_chat_ids('-100, -200 ,300') == [-100, -200, 300]

    def test_parse_chat_ids_empty(self):
        assert _parse_chat_ids('') == []

    def test_nsfw_names_filters_by_scope(self):
        registry = CommandRegistry.instance()
        registry.register(_Fake('porno', CommandScope.NSFW))
        registry.register(_Fake('oi', CommandScope.PUBLIC))

        assert _nsfw_command_names(registry) == ['porno']
