"""Random football player from Transfermarkt's most-valuable rankings."""

import random

import structlog

from bot.data.football import LEAGUE_CODES, LEAGUES, LeagueInfo
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    Flag,
    OptionDef,
    ParsedCommand,
    Platform,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.transfermarkt import TmPlayer, TransfermarktService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class FootballPlayerCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='jogador',
            options=[
                OptionDef(name='top', pattern=r'top\d+'),
                OptionDef(name='liga', values=LEAGUE_CODES),
            ],
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Jogador aleatório do top de mais valiosos. Use --liga <código> e top<N>.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        league = LEAGUES.get(liga_code) if liga_code else None
        top_str = parsed.options.get('top', '')

        default_max = (
            TransfermarktService.LEAGUE_MAX_PAGES
            if league
            else TransfermarktService.GLOBAL_MAX_PAGES
        )

        if top_str:
            top_n = int(top_str[3:])
            max_page = max(
                1,
                min(
                    (top_n + TransfermarktService.PLAYERS_PER_PAGE - 1)
                    // TransfermarktService.PLAYERS_PER_PAGE,
                    default_max,
                ),
            )
        else:
            max_page = default_max

        page = random.randint(1, max_page)  # noqa: S311
        players = await TransfermarktService.fetch_page(page, league)

        if top_str and players and page == max_page:
            top_n = int(top_str[3:])
            items_on_last_page = top_n - (max_page - 1) * TransfermarktService.PLAYERS_PER_PAGE
            players = players[:items_on_last_page]

        if not players:
            return [Reply.to(data).text('Nenhum jogador encontrado. Tente novamente! ⚽')]

        player = random.choice(players)  # noqa: S311
        caption = self._build_caption(player, league)
        buffer = await HttpClient.get_buffer(player.photo_url, headers=TransfermarktService.HEADERS)
        return [Reply.to(data).image_buffer(buffer, caption)]

    @staticmethod
    def _build_caption(player: TmPlayer, league: LeagueInfo | None) -> str:
        club_flag = league.flag if league else ''
        return (
            f'*{player.name}* — {player.position}\n\n'
            f'🎂 {player.age} anos   🌍 {player.nationality}\n'
            f'🏟️ {player.club} {club_flag}\n\n'
            f'💰 {player.market_value}'
        )
