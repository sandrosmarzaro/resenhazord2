import pytest

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.pokemon import PokemonCommand
from bot.infrastructure.llm.agent_feedback import AgentFeedback


class TestRecalls:
    @pytest.fixture(autouse=True)
    def _pokemon(self):
        CommandRegistry.instance().register(PokemonCommand())

    def test_an_unaccented_spelling_is_the_same_command(self):
        assert AgentFeedback.recalls([',pokemon booster'], ',pokémon team')

    def test_another_command_is_a_miss(self):
        assert not AgentFeedback.recalls([',carro'], ',pokémon')

    def test_an_unknown_command_is_never_recalled(self):
        assert not AgentFeedback.recalls([',xyz'], ',xyz')
