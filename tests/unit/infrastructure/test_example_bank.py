import pytest

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandConfig, CommandScope
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.models.retrieved_example import RetrievedExample
from bot.infrastructure.llm.example_bank import build_example_bank


class _StubCommand(Command):
    def __init__(self, config: CommandConfig, description: str) -> None:
        super().__init__()
        self._config = config
        self._description = description

    @property
    def config(self) -> CommandConfig:
        return self._config

    @property
    def menu_description(self) -> str:
        return self._description

    async def execute(self, data: CommandData, parsed: object) -> list[BotMessage]:
        return []


@pytest.fixture
def registry() -> CommandRegistry:
    registry = CommandRegistry.instance()
    registry.register(
        _StubCommand(
            CommandConfig(name='carro', aliases=['car']),
            'foto de carro aleatório',
        )
    )
    return registry


class TestGeneratedBaseline:
    def test_includes_command_name(self, registry):
        bank = build_example_bank(registry, hand_examples=[])

        assert RetrievedExample(text='carro', command=',carro') in bank

    def test_includes_aliases(self, registry):
        bank = build_example_bank(registry, hand_examples=[])

        assert RetrievedExample(text='car', command=',carro') in bank

    def test_includes_menu_description(self, registry):
        bank = build_example_bank(registry, hand_examples=[])

        assert RetrievedExample(text='foto de carro aleatório', command=',carro') in bank


class TestScopeFiltering:
    def test_excludes_nsfw_commands(self, registry):
        registry.register(
            _StubCommand(CommandConfig(name='porno', scope=CommandScope.NSFW), 'nsfw')
        )

        bank = build_example_bank(registry, hand_examples=[])

        assert all(example.command != ',porno' for example in bank)


class TestHandAugmentation:
    def test_merges_hand_examples(self, registry):
        bank = build_example_bank(registry, hand_examples=[('rock pauleira', ',música rock')])

        assert RetrievedExample(text='rock pauleira', command=',música rock') in bank

    def test_dedups_identical_text(self, registry):
        bank = build_example_bank(registry, hand_examples=[('carro', ',carro')])

        matching = [example for example in bank if example.text == 'carro']
        assert len(matching) == 1
