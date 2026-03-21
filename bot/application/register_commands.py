"""Register all Python-side commands with the CommandRegistry."""

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.add import AddCommand
from bot.domain.commands.adm import AdmCommand
from bot.domain.commands.alcorao import AlcoraoCommand
from bot.domain.commands.animal import AnimalCommand
from bot.domain.commands.audio import AudioCommand
from bot.domain.commands.ban import BanCommand
from bot.domain.commands.baralho import BaralhoCommand
from bot.domain.commands.beer import BeerCommand
from bot.domain.commands.biblia import BibliaCommand
from bot.domain.commands.bicho import BichoCommand
from bot.domain.commands.borges import BorgesCommand
from bot.domain.commands.carro import CarroCommand
from bot.domain.commands.clash_royale import ClashRoyaleCommand
from bot.domain.commands.country_flag import CountryFlagCommand
from bot.domain.commands.d20 import D20Command
from bot.domain.commands.dev import DevCommand
from bot.domain.commands.download import DownloadCommand
from bot.domain.commands.drive import DriveCommand
from bot.domain.commands.extrair import ExtrairCommand
from bot.domain.commands.fato import FatoCommand
from bot.domain.commands.filme_serie import FilmeSerieCommand
from bot.domain.commands.fuck import FuckCommand
from bot.domain.commands.game import GameCommand
from bot.domain.commands.group_mentions import GroupMentionsCommand
from bot.domain.commands.hearthstone import HearthstoneCommand
from bot.domain.commands.hentai import HentaiCommand
from bot.domain.commands.jackpot import JackpotCommand
from bot.domain.commands.league_of_legends import LeagueOfLegendsCommand
from bot.domain.commands.lua import LuaCommand
from bot.domain.commands.magic_the_gathering import MagicTheGatheringCommand
from bot.domain.commands.mateus import MateusCommand
from bot.domain.commands.meal_recipes import MealRecipesCommand
from bot.domain.commands.menu import MenuCommand
from bot.domain.commands.music import MusicCommand
from bot.domain.commands.my_anime_list import MyAnimeListCommand
from bot.domain.commands.oi import OiCommand
from bot.domain.commands.pokemon import PokemonCommand
from bot.domain.commands.pokemon_tcg import PokemonTCGCommand
from bot.domain.commands.porno import PornoCommand
from bot.domain.commands.puppy import PuppyCommand
from bot.domain.commands.rule34 import Rule34Command
from bot.domain.commands.scarra import ScarraCommand
from bot.domain.commands.sticker import StickerCommand
from bot.domain.commands.torah import TorahCommand
from bot.domain.commands.yugioh import YugiohCommand
from bot.domain.services.discord import DiscordService
from bot.infrastructure.mongodb import MongoDBConnection
from bot.settings import Settings


def register_all_commands(settings: Settings | None = None) -> None:
    if settings is None:
        settings = Settings()

    MongoDBConnection.configure(settings.mongodb_uri)

    registry = CommandRegistry.instance()
    registry.register(AddCommand(bot_jid=settings.resenhazord2_jid))
    registry.register(AdmCommand())
    registry.register(AlcoraoCommand())
    registry.register(AnimalCommand())
    registry.register(AudioCommand())
    registry.register(BaralhoCommand())
    registry.register(BeerCommand())
    registry.register(BibliaCommand(biblia_token=settings.biblia_token))
    registry.register(BichoCommand())
    registry.register(BanCommand(bot_jid=settings.resenhazord2_jid))
    registry.register(BorgesCommand())
    registry.register(CarroCommand())
    registry.register(ClashRoyaleCommand())
    registry.register(CountryFlagCommand())
    registry.register(D20Command())
    registry.register(DevCommand())
    registry.register(DownloadCommand())
    registry.register(
        DriveCommand(
            discord=DiscordService(settings.discord_token, settings.discord_guild_id)
            if settings.discord_token and settings.discord_guild_id
            else None
        )
    )
    registry.register(ExtrairCommand())
    registry.register(FatoCommand())
    registry.register(FilmeSerieCommand(tmdb_api_key=settings.tmdb_api_key))
    registry.register(
        GameCommand(
            twitch_client_id=settings.twitch_client_id,
            twitch_client_secret=settings.twitch_client_secret,
            rawg_api_key=settings.rawg_api_key,
        )
    )
    registry.register(GroupMentionsCommand())
    registry.register(HentaiCommand())
    registry.register(JackpotCommand())
    registry.register(FuckCommand())
    registry.register(
        HearthstoneCommand(bnet_id=settings.bnet_id, bnet_secret=settings.bnet_secret)
    )
    registry.register(LeagueOfLegendsCommand())
    registry.register(LuaCommand())
    registry.register(MagicTheGatheringCommand())
    registry.register(MateusCommand())
    registry.register(MealRecipesCommand())
    registry.register(MenuCommand())
    registry.register(MusicCommand(jamendo_client_id=settings.jamendo_client_id))
    registry.register(MyAnimeListCommand())
    registry.register(OiCommand())
    registry.register(PokemonCommand())
    registry.register(PokemonTCGCommand())
    registry.register(PornoCommand())
    registry.register(PuppyCommand())
    registry.register(Rule34Command())
    registry.register(ScarraCommand())
    registry.register(StickerCommand())
    registry.register(TorahCommand())
    registry.register(YugiohCommand())
