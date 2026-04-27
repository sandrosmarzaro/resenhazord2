import inspect
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from discord import app_commands

from bot.adapters.discord.bot import DiscordBot
from bot.adapters.discord.slash_register import DiscordSlashRegistrar
from bot.domain.commands.base import ArgType, Command, CommandConfig, OptionDef, Platform


@pytest.fixture
def fake_command(mocker):
    def _build(config: CommandConfig, description: str = 'Test description'):
        cmd = mocker.MagicMock(spec=Command)
        cmd.config = config
        cmd.menu_description = description
        return cmd

    return _build


def _patch_registry(mocker, commands: list) -> None:
    mock_registry = mocker.patch('bot.adapters.discord.slash_register.CommandRegistry')
    mock_registry.instance.return_value.get_all.return_value = commands


class TestNormalizeName:
    def test_strips_diacritics(self):
        assert DiscordSlashRegistrar._normalize_name('horóscopo') == 'horoscopo'

    def test_strips_accented_letters(self):
        assert DiscordSlashRegistrar._normalize_name('pokémon') == 'pokemon'

    def test_spaces_become_hyphens(self):
        assert DiscordSlashRegistrar._normalize_name('rule 34') == 'rule-34'

    def test_strips_cedilla(self):
        assert DiscordSlashRegistrar._normalize_name('áudio') == 'audio'

    def test_truncates_to_max_length(self):
        long_name = 'a' * 50
        result = DiscordSlashRegistrar._normalize_name(long_name)
        assert len(result) == DiscordSlashRegistrar.NAME_MAX_LENGTH

    def test_plain_ascii_unchanged(self):
        assert DiscordSlashRegistrar._normalize_name('d20') == 'd20'

    def test_removes_invalid_chars(self):
        assert DiscordSlashRegistrar._normalize_name('hello!world') == 'helloworld'

    def test_aliases_normalising_to_same_root_collapse(self):
        aliases = ['rule 34', 'rule_34', 'rule-34', 'rule34']
        normalized = [DiscordSlashRegistrar._normalize_name(a) for a in aliases]

        assert len(set(normalized)) == 3


class TestBuildSignature:
    def test_minimal_config_has_only_interaction(self):
        sig = DiscordSlashRegistrar._build_signature(CommandConfig(name='test'))

        assert list(sig.parameters.keys()) == ['interaction']

    def test_option_with_values_adds_string_param(self):
        config = CommandConfig(name='test', options=[OptionDef(name='type', values=['a', 'b'])])
        sig = DiscordSlashRegistrar._build_signature(config)

        param = sig.parameters['type']
        assert param.default is None
        assert param.annotation == (str | None)

    def test_option_with_pattern_adds_string_param(self):
        config = CommandConfig(
            name='test',
            options=[OptionDef(name='lang', pattern=r'[A-Za-z]{2}-[A-Za-z]{2}')],
        )
        sig = DiscordSlashRegistrar._build_signature(config)

        param = sig.parameters['lang']
        assert param.default is None
        assert param.annotation == (str | None)

    def test_whatsapp_only_flags_skipped(self):
        config = CommandConfig(name='test', flags=['dm', 'show', 'detail'])
        sig = DiscordSlashRegistrar._build_signature(config)

        assert 'dm' not in sig.parameters
        assert 'show' not in sig.parameters
        assert 'detail' in sig.parameters

    def test_flag_is_optional_bool(self):
        config = CommandConfig(name='test', flags=['detail'])
        sig = DiscordSlashRegistrar._build_signature(config)

        param = sig.parameters['detail']
        assert param.default is None
        assert param.annotation == (bool | None)

    def test_required_args_has_no_default(self):
        config = CommandConfig(name='test', args=ArgType.REQUIRED)
        sig = DiscordSlashRegistrar._build_signature(config)

        param = sig.parameters['args']
        assert param.default is inspect.Parameter.empty
        assert param.annotation is str

    def test_optional_args_default_is_none(self):
        config = CommandConfig(name='test', args=ArgType.OPTIONAL)
        sig = DiscordSlashRegistrar._build_signature(config)

        param = sig.parameters['args']
        assert param.default is None
        assert param.annotation == (str | None)

    def test_no_args_field_when_none(self):
        config = CommandConfig(name='test', args=ArgType.NONE)
        sig = DiscordSlashRegistrar._build_signature(config)

        assert 'args' not in sig.parameters


class TestRegisterAll:
    def test_skips_non_discord_platforms(self, mocker, fake_command):
        commands = [
            fake_command(CommandConfig(name='d20', platforms=[Platform.DISCORD])),
            fake_command(CommandConfig(name='sticker', platforms=[Platform.WHATSAPP])),
            fake_command(CommandConfig(name='jackpot', platforms=[Platform.DISCORD])),
        ]
        _patch_registry(mocker, commands)
        bot = DiscordBot('123456789')

        bot.register_commands()

        names = [cmd.name for cmd in bot._tree.get_commands()]
        assert names == ['d20', 'jackpot']

    def test_aliases_register_as_separate_commands(self, mocker, fake_command):
        cmd = fake_command(
            CommandConfig(name='anime', aliases=['manga'], platforms=[Platform.DISCORD])
        )
        _patch_registry(mocker, [cmd])
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
        _patch_registry(mocker, [cmd])
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
        _patch_registry(mocker, [cmd])
        bot = DiscordBot('123456789')

        bot.register_commands()

        registered = bot._tree.get_commands()
        assert len(registered) == 1
        assert registered[0].name == 'd20'
