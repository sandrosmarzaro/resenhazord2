from typing import Any, cast

import pytest
from telegram.error import TelegramError

from bot.adapters.telegram.bot import TelegramBot
from bot.domain.commands.base import CommandScope, Platform
from tests.unit.adapters.telegram.conftest import FakeCommand

FAKE_TOKEN = 'x' * 10


def _patch_registry(mocker, commands):
    registry = mocker.MagicMock(get_all=mocker.MagicMock(return_value=commands))
    mocker.patch(
        'bot.adapters.telegram.bot.CommandRegistry.instance',
        return_value=registry,
    )
    return registry


def _make_bot(mocker, *, nsfw_chat_ids: frozenset[int] = frozenset()):
    mocker.patch('bot.adapters.telegram.bot.Application.builder')
    bot = TelegramBot(token=FAKE_TOKEN, bot_username='resenhazord_bot', nsfw_chat_ids=nsfw_chat_ids)
    bot._app = mocker.MagicMock()
    bot._app.bot = mocker.AsyncMock()
    return bot


class TestNormalizeName:
    def test_lowercase_ascii(self):
        assert TelegramBot._normalize_name('Hello') == 'hello'

    def test_strips_accents(self):
        assert TelegramBot._normalize_name('horóscopo') == 'horoscopo'

    def test_replaces_spaces_and_hyphens_with_underscore(self):
        assert TelegramBot._normalize_name('clash-royale') == 'clash_royale'
        assert TelegramBot._normalize_name('my command') == 'my_command'

    def test_drops_other_chars(self):
        assert TelegramBot._normalize_name('hi!@#') == 'hi'

    def test_caps_length(self):
        result = TelegramBot._normalize_name('a' * 50)
        assert len(result) == TelegramBot.NAME_MAX_LENGTH


class TestIsMenuEligible:
    def test_public_command_with_telegram_platform(self):
        cmd = FakeCommand('ok', platforms=[Platform.TELEGRAM])
        assert TelegramBot._is_menu_eligible(cmd, {CommandScope.PUBLIC}) is True

    def test_rejects_non_telegram_platform(self):
        cmd = FakeCommand('ok', platforms=[Platform.DISCORD])
        assert TelegramBot._is_menu_eligible(cmd, {CommandScope.PUBLIC}) is False

    def test_rejects_scope_outside_set(self):
        cmd = FakeCommand('ok', platforms=[Platform.TELEGRAM], scope=CommandScope.NSFW)
        assert TelegramBot._is_menu_eligible(cmd, {CommandScope.PUBLIC}) is False

    def test_accepts_nsfw_when_in_scope(self):
        cmd = FakeCommand('ok', platforms=[Platform.TELEGRAM], scope=CommandScope.NSFW)
        assert TelegramBot._is_menu_eligible(cmd, {CommandScope.PUBLIC, CommandScope.NSFW}) is True


class TestStartStop:
    @pytest.mark.anyio
    async def test_start_registers_handlers_and_polls(self, mocker):
        bot = _make_bot(mocker)
        bot._app.initialize = mocker.AsyncMock()
        bot._app.start = mocker.AsyncMock()
        updater_mock = mocker.MagicMock()
        updater_mock.start_polling = mocker.AsyncMock()
        bot._app.updater = updater_mock
        bot._publish_command_menu = mocker.AsyncMock()
        _patch_registry(mocker, [FakeCommand('oi', platforms=[Platform.TELEGRAM])])

        await bot.start()

        cast('Any', bot._app.initialize).assert_called_once()
        cast('Any', bot._app.start).assert_called_once()
        cast('Any', updater_mock.start_polling).assert_called_once()

    @pytest.mark.anyio
    async def test_start_without_updater_skips_polling(self, mocker):
        bot = _make_bot(mocker)
        bot._app.initialize = mocker.AsyncMock()
        bot._app.start = mocker.AsyncMock()
        bot._app.updater = None
        bot._publish_command_menu = mocker.AsyncMock()
        _patch_registry(mocker, [])

        await bot.start()

        cast('Any', bot._app.initialize).assert_called_once()

    @pytest.mark.anyio
    async def test_stop_shuts_down_app(self, mocker):
        bot = _make_bot(mocker)
        bot._app.stop = mocker.AsyncMock()
        bot._app.shutdown = mocker.AsyncMock()
        updater_mock = mocker.MagicMock()
        updater_mock.stop = mocker.AsyncMock()
        bot._app.updater = updater_mock

        await bot.stop()

        cast('Any', updater_mock.stop).assert_called_once()
        cast('Any', bot._app.stop).assert_called_once()
        cast('Any', bot._app.shutdown).assert_called_once()

    @pytest.mark.anyio
    async def test_stop_without_updater(self, mocker):
        bot = _make_bot(mocker)
        bot._app.stop = mocker.AsyncMock()
        bot._app.shutdown = mocker.AsyncMock()
        bot._app.updater = None

        await bot.stop()

        cast('Any', bot._app.stop).assert_called_once()


class TestRegisterHandlers:
    @pytest.mark.anyio
    async def test_registers_telegram_commands(self, mocker):
        commands = [
            FakeCommand('oi', platforms=[Platform.TELEGRAM]),
            FakeCommand('skip', platforms=[Platform.DISCORD]),
        ]
        _patch_registry(mocker, commands)
        bot = _make_bot(mocker)

        bot._register_handlers()

        add_handler_calls = cast('Any', bot._app.add_handler).call_args_list
        command_handlers = [c for c in add_handler_calls if c.args[0]]
        assert len(command_handlers) >= 2

    @pytest.mark.anyio
    async def test_registers_aliases(self, mocker):
        commands = [FakeCommand('oi', platforms=[Platform.TELEGRAM], aliases=['ola', 'hi'])]
        _patch_registry(mocker, commands)
        bot = _make_bot(mocker)

        bot._register_handlers()

        assert bot._handler._name_map.get('ola') == ',ola'
        assert bot._handler._name_map.get('hi') == ',hi'

    @pytest.mark.anyio
    async def test_registers_start_alias_when_menu_exists(self, mocker):
        menu_cmd = FakeCommand('menu', platforms=[Platform.TELEGRAM])
        registry = _patch_registry(mocker, [menu_cmd])
        registry.get_by_name.return_value = menu_cmd
        bot = _make_bot(mocker)

        bot._register_handlers()

        assert bot._handler._name_map.get('start') == ',menu'

    @pytest.mark.anyio
    async def test_skips_start_alias_when_menu_not_telegram(self, mocker):
        menu_cmd = FakeCommand('menu', platforms=[Platform.DISCORD])
        registry = _patch_registry(mocker, [menu_cmd])
        registry.get_by_name.return_value = menu_cmd
        bot = _make_bot(mocker)

        bot._register_handlers()

        assert 'start' not in bot._handler._name_map

    @pytest.mark.anyio
    async def test_skips_start_alias_when_no_menu_command(self, mocker):
        registry = _patch_registry(mocker, [])
        registry.get_by_name.return_value = None
        bot = _make_bot(mocker)

        bot._register_handlers()

        assert 'start' not in bot._handler._name_map


class TestMakeCallback:
    @pytest.mark.anyio
    async def test_callback_delegates_to_handler(self, mocker):
        bot = _make_bot(mocker)
        _patch_registry(mocker, [])
        handle_mock = mocker.patch.object(bot._handler, 'handle', mocker.AsyncMock())

        callback = bot._make_callback()
        fake_update = mocker.MagicMock()
        fake_context = mocker.MagicMock()
        fake_context.bot = mocker.MagicMock()

        await callback(fake_update, fake_context)

        handle_mock.assert_called_once()


class TestPublishCommandMenu:
    @pytest.fixture
    def bot(self, mocker):
        return _make_bot(mocker)

    @pytest.fixture
    def commands(self):
        return [
            FakeCommand('oi', platforms=[Platform.TELEGRAM]),
            FakeCommand('hentai', platforms=[Platform.TELEGRAM], scope=CommandScope.NSFW),
            FakeCommand('off', platforms=[Platform.DISCORD]),
        ]

    @pytest.mark.anyio
    async def test_publishes_only_public_by_default(self, bot, commands, mocker):
        _patch_registry(mocker, commands)

        await bot._publish_command_menu()

        bot._app.bot.set_my_commands.assert_called_once()
        published = bot._app.bot.set_my_commands.call_args.args[0]
        assert [c.command for c in published] == ['oi']

    @pytest.mark.anyio
    async def test_publishes_aliases_alongside_primary(self, bot, mocker):
        commands = [
            FakeCommand(
                'figurinha',
                platforms=[Platform.TELEGRAM],
                aliases=['fig', 'sticker'],
                description='gera sticker',
            ),
        ]
        _patch_registry(mocker, commands)

        await bot._publish_command_menu()

        published = bot._app.bot.set_my_commands.call_args.args[0]
        assert [c.command for c in published] == ['figurinha', 'fig', 'sticker']
        assert {c.description for c in published} == {'gera sticker'}

    @pytest.mark.anyio
    async def test_skips_alias_that_normalizes_to_existing_name(self, bot, mocker):
        commands = [FakeCommand('oi', platforms=[Platform.TELEGRAM], aliases=['Oi', 'hi'])]
        _patch_registry(mocker, commands)

        await bot._publish_command_menu()

        published = bot._app.bot.set_my_commands.call_args.args[0]
        assert [c.command for c in published] == ['oi', 'hi']

    @pytest.mark.anyio
    async def test_api_failure_is_logged_and_swallowed(self, bot, commands, mocker):
        _patch_registry(mocker, commands)
        bot._app.bot.set_my_commands.side_effect = TelegramError('rate limited')

        await bot._publish_command_menu()

        bot._app.bot.set_my_commands.assert_called_once()

    @pytest.mark.anyio
    async def test_publishes_nsfw_per_chat(self, commands, mocker):
        bot = _make_bot(mocker, nsfw_chat_ids=frozenset({42, 99}))
        _patch_registry(mocker, commands)

        await bot._publish_command_menu()

        set_commands = cast('Any', bot._app.bot.set_my_commands)
        assert set_commands.call_count == 3
        nsfw_calls = [call for call in set_commands.call_args_list if 'scope' in call.kwargs]
        assert len(nsfw_calls) == 2
        published_names = {c.command for c in nsfw_calls[0].args[0]}
        assert published_names == {'oi', 'hentai'}
