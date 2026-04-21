"""Register all Python-side commands with the CommandRegistry."""

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.add import AddCommand
from bot.domain.commands.adm import AdmCommand
from bot.domain.commands.animal import AnimalCommand
from bot.domain.commands.audio import AudioCommand
from bot.domain.commands.ban import BanCommand
from bot.domain.commands.beer import BeerCommand
from bot.domain.commands.bible import BibleCommand
from bot.domain.commands.borges import BorgesCommand
from bot.domain.commands.car import CarCommand
from bot.domain.commands.clash_royale import ClashRoyaleCommand
from bot.domain.commands.country_flag import CountryFlagCommand
from bot.domain.commands.currency import CurrencyCommand
from bot.domain.commands.d20 import D20Command
from bot.domain.commands.dev import DevCommand
from bot.domain.commands.download import DownloadCommand
from bot.domain.commands.drive import DriveCommand
from bot.domain.commands.extract import ExtractCommand
from bot.domain.commands.fact import FactCommand
from bot.domain.commands.fipe import FipeCommand
from bot.domain.commands.football_player import FootballPlayerCommand
from bot.domain.commands.football_standings import FootballStandingsCommand
from bot.domain.commands.football_team import FootballTeamCommand
from bot.domain.commands.fuck import FuckCommand
from bot.domain.commands.game import GameCommand
from bot.domain.commands.group_mentions import GroupMentionsCommand
from bot.domain.commands.hearthstone import HearthstoneCommand
from bot.domain.commands.hentai import HentaiCommand
from bot.domain.commands.horoscope import HoroscopeCommand
from bot.domain.commands.jackpot import JackpotCommand
from bot.domain.commands.league_of_legends import LeagueOfLegendsCommand
from bot.domain.commands.lottery import LotteryCommand
from bot.domain.commands.magic_the_gathering import MagicTheGatheringCommand
from bot.domain.commands.mateus import MateusCommand
from bot.domain.commands.meal_recipes import MealRecipesCommand
from bot.domain.commands.menu import MenuCommand
from bot.domain.commands.moon import MoonCommand
from bot.domain.commands.movie_series import MovieSeriesCommand
from bot.domain.commands.music import MusicCommand
from bot.domain.commands.my_anime_list import MyAnimeListCommand
from bot.domain.commands.oi import OiCommand
from bot.domain.commands.playing_card import PlayingCardCommand
from bot.domain.commands.pokemon import PokemonCommand
from bot.domain.commands.pokemon_tcg import PokemonTCGCommand
from bot.domain.commands.porno import PornoCommand
from bot.domain.commands.puppy import PuppyCommand
from bot.domain.commands.quran import QuranCommand
from bot.domain.commands.rule34 import Rule34Command
from bot.domain.commands.score import ScoreCommand
from bot.domain.commands.spit import SpitCommand
from bot.domain.commands.sticker import StickerCommand
from bot.domain.commands.torah import TorahCommand
from bot.domain.commands.yugioh import YugiohCommand
from bot.domain.services.discord import DiscordService
from bot.infrastructure.mongodb import MongoDBConnection
from bot.settings import Settings


def register_all_commands(settings: Settings | None = None) -> None:
    if settings is None:
        settings = Settings()

    MongoDBConnection.configure(settings.mongodb_uri, settings.mongodb_db_name)

    from bot.infrastructure.llm.provider_chain import configure_chain
    configure_chain(settings.github_token, settings.mistral_api_key, settings.groq_api_key)

    registry = CommandRegistry.instance()
    _register_simple_commands(registry)
    _register_configured_commands(registry, settings)


def _register_simple_commands(registry: CommandRegistry) -> None:
    registry.register(AdmCommand())
    registry.register(QuranCommand())
    registry.register(AnimalCommand())
    registry.register(AudioCommand())
    registry.register(PlayingCardCommand())
    registry.register(BeerCommand())
    registry.register(LotteryCommand())
    registry.register(BorgesCommand())
    registry.register(CarCommand())
    registry.register(ClashRoyaleCommand())
    registry.register(CountryFlagCommand())
    registry.register(CurrencyCommand())
    registry.register(D20Command())
    registry.register(DevCommand())
    registry.register(DownloadCommand())
    registry.register(ExtractCommand())
    registry.register(FactCommand())
    registry.register(FipeCommand())
    registry.register(FootballPlayerCommand())
    registry.register(FootballStandingsCommand())
    registry.register(FootballTeamCommand())
    registry.register(GroupMentionsCommand())
    registry.register(HoroscopeCommand())
    registry.register(JackpotCommand())
    registry.register(FuckCommand())
    registry.register(LeagueOfLegendsCommand())
    registry.register(MoonCommand())
    registry.register(MagicTheGatheringCommand())
    registry.register(MateusCommand())
    registry.register(MealRecipesCommand())
    registry.register(MenuCommand())
    registry.register(MyAnimeListCommand())
    registry.register(OiCommand())
    registry.register(PokemonCommand())
    registry.register(PokemonTCGCommand())
    registry.register(ScoreCommand())
    registry.register(PornoCommand())
    registry.register(PuppyCommand())
    registry.register(Rule34Command())
    registry.register(SpitCommand())
    registry.register(StickerCommand())
    registry.register(TorahCommand())
    registry.register(YugiohCommand())


def _register_configured_commands(registry: CommandRegistry, settings: Settings) -> None:
    registry.register(AddCommand(bot_jid=settings.resenhazord2_jid))
    registry.register(BanCommand(bot_jid=settings.resenhazord2_jid))
    registry.register(BibleCommand(biblia_token=settings.biblia_token))
    registry.register(
        DriveCommand(
            discord=DiscordService(settings.discord_token, settings.discord_drive_guild_id)
            if settings.discord_token and settings.discord_drive_guild_id
            else None
        )
    )
    registry.register(
        MovieSeriesCommand(tmdb_api_key=settings.tmdb_api_key, omdb_api_key=settings.omdb_api_key)
    )
    registry.register(
        GameCommand(
            twitch_client_id=settings.twitch_client_id,
            twitch_client_secret=settings.twitch_client_secret,
            rawg_api_key=settings.rawg_api_key,
        )
    )
    registry.register(
        HearthstoneCommand(bnet_id=settings.bnet_id, bnet_secret=settings.bnet_secret)
    )
    registry.register(HentaiCommand(nhentai_mirror_url=settings.nhentai_mirror_url))
    registry.register(MusicCommand(jamendo_client_id=settings.jamendo_client_id))
