import inspect
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from discord import app_commands

from bot.adapters.discord.bot import DiscordBot
from bot.domain.commands.base import ArgType, Command, CommandConfig, OptionDef, Platform


class TestNormalizeName:
    def test_strips_diacritics(self):
        assert DiscordBot._normalize_name('horóscopo') == 'horoscopo'

    def test_strips_accented_letters(self):
        assert DiscordBot._normalize_name('pokémon') == 'pokemon'

    def test_spaces_become_hyphens(self):
        assert DiscordBot._normalize_name('rule 34') == 'rule-34'

    def test_strips_cedilla(self):
        assert DiscordBot._normalize_name('áudio') == 'audio'

    def test_truncates_to_max_length(self):
        long_name = 'a' * 50
        result = DiscordBot._normalize_name(long_name)
        assert len(result) == DiscordBot.DISCORD_NAME_MAX_LENGTH

    def test_plain_ascii_unchanged(self):
        assert DiscordBot._normalize_name('d20') == 'd20'

    def test_removes_invalid_chars(self):
        assert DiscordBot._normalize_name('hello!world') == 'helloworld'


class TestBuildSignature:
    def test_minimal_config_has_only_interaction(self):
        config = CommandConfig(name='test')
        sig = DiscordBot._build_signature(config)

        assert list(sig.parameters.keys()) == ['interaction']

    def test_option_adds_string_param(self):
        config = CommandConfig(
            name='test',
            options=[OptionDef(name='type', values=['a', 'b'])],
        )
        sig = DiscordBot._build_signature(config)

        assert 'type' in sig.parameters
        param = sig.parameters['type']
        assert param.default is None
        assert param.annotation == (str | None)

    def test_whatsapp_flags_skipped(self):
        config = CommandConfig(name='test', flags=['dm', 'show', 'detail'])
        sig = DiscordBot._build_signature(config)

        assert 'dm' not in sig.parameters
        assert 'show' not in sig.parameters
        assert 'detail' in sig.parameters

    def test_flag_is_bool_optional(self):
        config = CommandConfig(name='test', flags=['detail'])
        sig = DiscordBot._build_signature(config)

        param = sig.parameters['detail']
        assert param.default is None
        assert param.annotation == (bool | None)

    def test_required_args_has_no_default(self):
        config = CommandConfig(name='test', args=ArgType.REQUIRED)
        sig = DiscordBot._build_signature(config)

        assert 'args' in sig.parameters
        param = sig.parameters['args']
        assert param.default is inspect.Parameter.empty
        assert param.annotation is str

    def test_optional_args_has_none_default(self):
        config = CommandConfig(name='test', args=ArgType.OPTIONAL)
        sig = DiscordBot._build_signature(config)

        param = sig.parameters['args']
        assert param.default is None
        assert param.annotation == (str | None)

    def test_no_args_field_when_none(self):
        config = CommandConfig(name='test', args=ArgType.NONE)
        sig = DiscordBot._build_signature(config)

        assert 'args' not in sig.parameters

    def test_pattern_option_adds_string_param(self):
        config = CommandConfig(
            name='test',
            options=[OptionDef(name='lang', pattern=r'[A-Za-z]{2}-[A-Za-z]{2}')],
        )
        sig = DiscordBot._build_signature(config)

        assert 'lang' in sig.parameters
        param = sig.parameters['lang']
        assert param.default is None
        assert param.annotation == (str | None)


class TestRegisterCommands:
    @staticmethod
    def _make_command(mocker, config: CommandConfig, description: str = 'Test description'):
        cmd = mocker.MagicMock(spec=Command)
        cmd.config = config
        cmd.menu_description = description
        return cmd

    def test_only_registers_discord_commands(self, mocker):
        discord_cmd = self._make_command(
            mocker, CommandConfig(name='d20', platforms=[Platform.WHATSAPP, Platform.DISCORD])
        )
        whatsapp_only_cmd = self._make_command(
            mocker, CommandConfig(name='sticker', platforms=[Platform.WHATSAPP])
        )
        another_discord_cmd = self._make_command(
            mocker, CommandConfig(name='jackpot', platforms=[Platform.WHATSAPP, Platform.DISCORD])
        )

        mock_registry = mocker.patch('bot.adapters.discord.bot.CommandRegistry')
        mock_registry.instance.return_value.get_all.return_value = [
            discord_cmd,
            whatsapp_only_cmd,
            another_discord_cmd,
        ]
        bot = DiscordBot('123456789')
        bot.register_commands()

        added_names = [cmd.name for cmd in bot._tree.get_commands(guild=bot._guild)]
        assert 'd20' in added_names
        assert 'jackpot' in added_names
        assert 'sticker' not in added_names

    def test_aliases_registered_as_separate_commands(self, mocker):
        cmd = self._make_command(
            mocker,
            CommandConfig(
                name='anime', aliases=['manga'], platforms=[Platform.WHATSAPP, Platform.DISCORD]
            ),
        )

        mock_registry = mocker.patch('bot.adapters.discord.bot.CommandRegistry')
        mock_registry.instance.return_value.get_all.return_value = [cmd]
        bot = DiscordBot('123456789')
        bot.register_commands()

        added_names = [c.name for c in bot._tree.get_commands(guild=bot._guild)]
        assert 'anime' in added_names
        assert 'manga' in added_names

    def test_command_with_option_gets_choices(self, mocker):
        cmd = self._make_command(
            mocker,
            CommandConfig(
                name='stic',
                options=[OptionDef(name='type', values=['crop', 'full'])],
                platforms=[Platform.WHATSAPP, Platform.DISCORD],
            ),
        )

        mock_registry = mocker.patch('bot.adapters.discord.bot.CommandRegistry')
        mock_registry.instance.return_value.get_all.return_value = [cmd]
        bot = DiscordBot('123456789')
        bot.register_commands()

        registered = bot._tree.get_commands(guild=bot._guild)
        assert len(registered) == 1
        slash = cast('app_commands.Command', registered[0])
        type_param = slash._params.get('type')
        assert type_param is not None
        assert len(type_param.choices) == 2
        choice_values = [c.value for c in type_param.choices]
        assert 'crop' in choice_values
        assert 'full' in choice_values
