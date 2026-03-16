"""Register all Python-side commands with the CommandRegistry."""

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.alcorao import AlcoraoCommand
from bot.domain.commands.baralho import BaralhoCommand
from bot.domain.commands.clash_royale import ClashRoyaleCommand
from bot.domain.commands.country_flag import CountryFlagCommand
from bot.domain.commands.d20 import D20Command
from bot.domain.commands.fato import FatoCommand
from bot.domain.commands.league_of_legends import LeagueOfLegendsCommand
from bot.domain.commands.mateus import MateusCommand
from bot.domain.commands.meal_recipes import MealRecipesCommand
from bot.domain.commands.oi import OiCommand
from bot.domain.commands.puppy import PuppyCommand


def register_all_commands() -> None:
    registry = CommandRegistry.instance()
    registry.register(AlcoraoCommand())
    registry.register(BaralhoCommand())
    registry.register(ClashRoyaleCommand())
    registry.register(CountryFlagCommand())
    registry.register(D20Command())
    registry.register(FatoCommand())
    registry.register(LeagueOfLegendsCommand())
    registry.register(MateusCommand())
    registry.register(MealRecipesCommand())
    registry.register(OiCommand())
    registry.register(PuppyCommand())
