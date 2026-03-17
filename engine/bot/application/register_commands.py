"""Register all Python-side commands with the CommandRegistry."""

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.alcorao import AlcoraoCommand
from bot.domain.commands.audio import AudioCommand
from bot.domain.commands.baralho import BaralhoCommand
from bot.domain.commands.beer import BeerCommand
from bot.domain.commands.biblia import BibliaCommand
from bot.domain.commands.bicho import BichoCommand
from bot.domain.commands.clash_royale import ClashRoyaleCommand
from bot.domain.commands.country_flag import CountryFlagCommand
from bot.domain.commands.d20 import D20Command
from bot.domain.commands.fato import FatoCommand
from bot.domain.commands.filme_serie import FilmeSerieCommand
from bot.domain.commands.fuck import FuckCommand
from bot.domain.commands.hearthstone import HearthstoneCommand
from bot.domain.commands.league_of_legends import LeagueOfLegendsCommand
from bot.domain.commands.magic_the_gathering import MagicTheGatheringCommand
from bot.domain.commands.mateus import MateusCommand
from bot.domain.commands.meal_recipes import MealRecipesCommand
from bot.domain.commands.my_anime_list import MyAnimeListCommand
from bot.domain.commands.oi import OiCommand
from bot.domain.commands.pokemon_tcg import PokemonTCGCommand
from bot.domain.commands.porno import PornoCommand
from bot.domain.commands.puppy import PuppyCommand
from bot.domain.commands.rule34 import Rule34Command
from bot.domain.commands.torah import TorahCommand
from bot.domain.commands.yugioh import YugiohCommand
from bot.settings import Settings


def register_all_commands(settings: Settings | None = None) -> None:
    if settings is None:
        settings = Settings()

    registry = CommandRegistry.instance()
    registry.register(AlcoraoCommand())
    registry.register(AudioCommand())
    registry.register(BaralhoCommand())
    registry.register(BeerCommand())
    registry.register(BibliaCommand(biblia_token=settings.biblia_token))
    registry.register(BichoCommand())
    registry.register(ClashRoyaleCommand())
    registry.register(CountryFlagCommand())
    registry.register(D20Command())
    registry.register(FatoCommand())
    registry.register(FilmeSerieCommand(tmdb_api_key=settings.tmdb_api_key))
    registry.register(FuckCommand())
    registry.register(
        HearthstoneCommand(bnet_id=settings.bnet_id, bnet_secret=settings.bnet_secret)
    )
    registry.register(LeagueOfLegendsCommand())
    registry.register(MagicTheGatheringCommand())
    registry.register(MateusCommand())
    registry.register(MealRecipesCommand())
    registry.register(MyAnimeListCommand())
    registry.register(OiCommand())
    registry.register(PokemonTCGCommand())
    registry.register(PornoCommand())
    registry.register(PuppyCommand())
    registry.register(Rule34Command())
    registry.register(TorahCommand())
    registry.register(YugiohCommand())
