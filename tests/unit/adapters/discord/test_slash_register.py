from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from discord import app_commands

from bot.adapters.discord.bot import DiscordBot
from bot.domain.commands.base import ArgType, CommandConfig, OptionDef, Platform
from tests.unit.adapters.discord.conftest import patch_slash_registry


class TestRegisterAll:
    def test_skips_non_discord_platforms(self, mocker, fake_command):
        commands = [
            fake_command(CommandConfig(name='d20', platforms=[Platform.DISCORD])),
            fake_command(CommandConfig(name='sticker', platforms=[Platform.WHATSAPP])),
            fake_command(CommandConfig(name='jackpot', platforms=[Platform.DISCORD])),
        ]
        patch_slash_registry(mocker, commands)
        bot = DiscordBot('123456789')

        bot.register_commands()

        names = [cmd.name for cmd in bot._tree.get_commands()]
        assert names == ['d20', 'jackpot']

    def test_aliases_register_as_separate_commands(self, mocker, fake_command):
        cmd = fake_command(
            CommandConfig(name='anime', aliases=['manga'], platforms=[Platform.DISCORD])
        )
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        names = [c.name for c in bot._tree.get_commands()]
        assert 'anime' in names
        assert 'manga' in names

    def test_options_with_values_become_choices(self, mocker, fake_command):
        cmd = fake_command(
            CommandConfig(
                name='stic',
                options=[OptionDef(name='type', values=['crop', 'full'])],
                platforms=[Platform.DISCORD],
            )
        )
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        registered = bot._tree.get_commands()
        slash = cast('app_commands.Command', registered[0])
        type_param = slash._params.get('type')
        assert type_param is not None
        choice_values = [c.value for c in type_param.choices]
        assert choice_values == ['crop', 'full']

    def test_commands_registered_globally(self, mocker, fake_command):
        cmd = fake_command(CommandConfig(name='d20', platforms=[Platform.DISCORD]))
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        registered = bot._tree.get_commands()
        assert len(registered) == 1
        assert registered[0].name == 'd20'


class TestMakeCallback:
    @pytest.mark.anyio
    async def test_callback_invokes_handler(self, mocker, fake_command):
        cmd = fake_command(CommandConfig(name='d20', platforms=[Platform.DISCORD]))
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')
        bot.register_commands()

        callback = bot._registrar._make_callback()
        interaction = mocker.MagicMock()
        handler_mock = mocker.patch.object(bot._handler, 'handle', mocker.AsyncMock())

        await callback(interaction)  # type: ignore[call-arg]

        handler_mock.assert_called_once()


class TestDuplicateCommand:
    def test_duplicate_name_skipped(self, mocker, fake_command):
        cmd = fake_command(CommandConfig(name='d20', aliases=['d20'], platforms=[Platform.DISCORD]))
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        names = [c.name for c in bot._tree.get_commands()]
        assert names.count('d20') == 1


class TestConfigureOptions:
    def test_option_without_values_no_choices(self, mocker, fake_command):
        cmd = fake_command(
            CommandConfig(
                name='test',
                options=[OptionDef(name='type', pattern=r'\d+')],
                platforms=[Platform.DISCORD],
            )
        )
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        registered = bot._tree.get_commands()
        slash = cast('app_commands.Command', registered[0])
        type_param = slash._params.get('type')
        assert type_param is not None

    def test_option_with_description(self, mocker, fake_command):
        cmd = fake_command(
            CommandConfig(
                name='test',
                options=[OptionDef(name='type', values=['a', 'b'], description='Pick one')],
                platforms=[Platform.DISCORD],
            )
        )
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        registered = bot._tree.get_commands()
        slash = cast('app_commands.Command', registered[0])
        type_param = slash._params.get('type')
        assert type_param is not None
        assert type_param.description == 'Pick one'

    def test_args_label_set_on_args_param(self, mocker, fake_command):
        cmd = fake_command(
            CommandConfig(
                name='test',
                args=ArgType.OPTIONAL,
                args_label='Search query',
                platforms=[Platform.DISCORD],
            )
        )
        patch_slash_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        registered = bot._tree.get_commands()
        slash = cast('app_commands.Command', registered[0])
        args_param = slash._params.get('args')
        assert args_param is not None
        assert args_param.description == 'Search query'
