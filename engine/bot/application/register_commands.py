"""Register all Python-side commands with the CommandRegistry."""

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.alcorao import AlcoraoCommand
from bot.domain.commands.baralho import BaralhoCommand
from bot.domain.commands.beer import BeerCommand
from bot.domain.commands.biblia import BibliaCommand
from bot.domain.commands.bicho import BichoCommand
from bot.domain.commands.clash_royale import ClashRoyaleCommand
from bot.domain.commands.country_flag import CountryFlagCommand
from bot.domain.commands.d20 import D20Command
from bot.domain.commands.fato import FatoCommand
from bot.domain.commands.filme_serie import FilmeSerieCommand
from bot.domain.commands.league_of_legends import LeagueOfLegendsCommand
from bot.domain.commands.mateus import MateusCommand
from bot.domain.commands.meal_recipes import MealRecipesCommand
from bot.domain.commands.my_anime_list import MyAnimeListCommand
from bot.domain.commands.oi import OiCommand
from bot.domain.commands.puppy import PuppyCommand
from bot.domain.commands.torah import TorahCommand


def register_all_commands() -> None:
    registry = CommandRegistry.instance()
    registry.register(AlcoraoCommand())
    registry.register(BaralhoCommand())
    registry.register(BeerCommand())
    registry.register(BibliaCommand())
    registry.register(BichoCommand())
    registry.register(ClashRoyaleCommand())
    registry.register(CountryFlagCommand())
    registry.register(D20Command())
    registry.register(FatoCommand())
    registry.register(FilmeSerieCommand())
    registry.register(LeagueOfLegendsCommand())
    registry.register(MateusCommand())
    registry.register(MealRecipesCommand())
    registry.register(MyAnimeListCommand())
    registry.register(OiCommand())
    registry.register(PuppyCommand())
    registry.register(TorahCommand())
