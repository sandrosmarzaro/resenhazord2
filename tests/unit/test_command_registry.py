from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class FakeCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='fake')

    @property
    def menu_description(self) -> str:
        return 'A fake command'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return []


class AnotherCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='another')

    @property
    def menu_description(self) -> str:
        return 'Another command'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return []


class TestCommandRegistry:
    def test_singleton(self):
        r1 = CommandRegistry.instance()
        r2 = CommandRegistry.instance()
        assert r1 is r2

    def test_reset(self):
        r1 = CommandRegistry.instance()
        CommandRegistry.reset()
        r2 = CommandRegistry.instance()
        assert r1 is not r2

    def test_register_and_get_strategy(self):
        registry = CommandRegistry.instance()
        registry.register(FakeCommand())

        assert registry.get_strategy(',fake') is not None
        assert registry.get_strategy(',unknown') is None

    def test_get_strategy_returns_first_match(self):
        registry = CommandRegistry.instance()
        cmd1 = FakeCommand()
        cmd2 = AnotherCommand()
        registry.register(cmd1)
        registry.register(cmd2)

        assert registry.get_strategy(',fake') is cmd1
        assert registry.get_strategy(',another') is cmd2

    def test_get_all(self):
        registry = CommandRegistry.instance()
        cmd1 = FakeCommand()
        cmd2 = AnotherCommand()
        registry.register(cmd1)
        registry.register(cmd2)

        all_cmds = registry.get_all()
        assert len(all_cmds) == 2
        assert cmd1 in all_cmds
        assert cmd2 in all_cmds


class TestGetByName:
    def test_returns_command_for_canonical_name(self):
        registry = CommandRegistry.instance()
        cmd = FakeCommand()
        registry.register(cmd)

        assert registry.get_by_name('fake') is cmd

    def test_lookup_is_case_insensitive(self):
        registry = CommandRegistry.instance()
        cmd = FakeCommand()
        registry.register(cmd)

        assert registry.get_by_name('FAKE') is cmd

    def test_returns_none_for_unknown_name(self):
        registry = CommandRegistry.instance()
        registry.register(FakeCommand())

        assert registry.get_by_name('missing') is None


class TestStrategyFastPath:
    def test_leading_token_lookup_returns_match_via_index(self, mocker):
        registry = CommandRegistry.instance()
        fake = FakeCommand()
        another = AnotherCommand()
        registry.register(fake)
        registry.register(another)
        spy = mocker.spy(another, 'matches')

        assert registry.get_strategy(',fake') is fake
        spy.assert_not_called()


class TestMultiWordAliasMatching:
    def test_rule_34_aliases_match_with_and_without_space(self):
        from bot.application.register_commands import register_all_commands
        from bot.settings import Settings

        register_all_commands(Settings())
        registry = CommandRegistry.instance()

        cmd = registry.get_by_name('rule 34')
        assert cmd is not None
        assert cmd.matches(',rule34') is True
        assert cmd.matches(',rule 34') is True
