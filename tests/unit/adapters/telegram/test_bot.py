import pytest

from bot.adapters.telegram.bot import TelegramBot
from bot.domain.commands.base import Category, Command, CommandConfig, CommandScope, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

FAKE_TOKEN = 'x' * 10


class FakeCommand(Command):
    def __init__(
        self,
        name: str,
        *,
        platforms: list[Platform],
        scope: CommandScope = CommandScope.PUBLIC,
        description: str = 'desc',
        aliases: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._name = name
        self._platforms = platforms
        self._scope = scope
        self._description = description
        self._aliases = aliases or []

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name=self._name,
            category=Category.OTHER,
            platforms=self._platforms,
            scope=self._scope,
            aliases=list(self._aliases),
        )

    @property
    def menu_description(self) -> str:
        return self._description

    async def execute(self, data: CommandData, parsed) -> list[BotMessage]:
        return []


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
        long_name = 'a' * 50

        result = TelegramBot._normalize_name(long_name)

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


class TestPublishCommandMenu:
    @pytest.fixture
    def bot(self, mocker):
        mocker.patch('bot.adapters.telegram.bot.Application.builder')
        instance = TelegramBot(
            token=FAKE_TOKEN, bot_username='resenhazord_bot', nsfw_chat_ids=frozenset()
        )
        instance._app = mocker.MagicMock()
        instance._app.bot = mocker.AsyncMock()
        return instance

    @pytest.fixture
    def commands(self):
        return [
            FakeCommand('oi', platforms=[Platform.TELEGRAM]),
            FakeCommand('hentai', platforms=[Platform.TELEGRAM], scope=CommandScope.NSFW),
            FakeCommand('off', platforms=[Platform.DISCORD]),
        ]

    @pytest.mark.anyio
    async def test_publishes_only_public_by_default(self, bot, commands, mocker):
        mocker.patch(
            'bot.adapters.telegram.bot.CommandRegistry.instance',
            return_value=mocker.MagicMock(get_all=mocker.MagicMock(return_value=commands)),
        )

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
        mocker.patch(
            'bot.adapters.telegram.bot.CommandRegistry.instance',
            return_value=mocker.MagicMock(get_all=mocker.MagicMock(return_value=commands)),
        )

        await bot._publish_command_menu()

        published = bot._app.bot.set_my_commands.call_args.args[0]
        assert [c.command for c in published] == ['figurinha', 'fig', 'sticker']
        assert {c.description for c in published} == {'gera sticker'}

    @pytest.mark.anyio
    async def test_skips_alias_that_normalizes_to_existing_name(self, bot, mocker):
        commands = [
            FakeCommand('oi', platforms=[Platform.TELEGRAM], aliases=['Oi', 'hi']),
        ]
        mocker.patch(
            'bot.adapters.telegram.bot.CommandRegistry.instance',
            return_value=mocker.MagicMock(get_all=mocker.MagicMock(return_value=commands)),
        )

        await bot._publish_command_menu()

        published = bot._app.bot.set_my_commands.call_args.args[0]
        assert [c.command for c in published] == ['oi', 'hi']

    @pytest.mark.anyio
    async def test_publishes_nsfw_per_chat(self, commands, mocker):
        mocker.patch('bot.adapters.telegram.bot.Application.builder')
        bot = TelegramBot(
            token=FAKE_TOKEN, bot_username='resenhazord_bot', nsfw_chat_ids=frozenset({42, 99})
        )
        bot._app = mocker.MagicMock()
        bot._app.bot = mocker.AsyncMock()
        mocker.patch(
            'bot.adapters.telegram.bot.CommandRegistry.instance',
            return_value=mocker.MagicMock(get_all=mocker.MagicMock(return_value=commands)),
        )

        await bot._publish_command_menu()

        assert bot._app.bot.set_my_commands.call_count == 3
        nsfw_calls = [
            call for call in bot._app.bot.set_my_commands.call_args_list if 'scope' in call.kwargs
        ]
        assert len(nsfw_calls) == 2
        published_names = {c.command for c in nsfw_calls[0].args[0]}
        assert published_names == {'oi', 'hentai'}
