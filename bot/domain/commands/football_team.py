"""Random football team with league standings and optional full lineup image."""

import asyncio
import random

import structlog

from bot.data.football import LEAGUE_CODES, LEAGUES, LeagueInfo
from bot.data.football_formations import random_formation
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
from bot.domain.models.football import SportsDBTeam, TmClub
from bot.domain.models.message import BotMessage
from bot.domain.services.full_lineup_builder import FullLineupBuilder
from bot.domain.services.global_top_team import GlobalTopTeam
from bot.domain.services.team_caption_builder import TeamCaptionBuilder
from bot.domain.services.thesportsdb import TheSportsDBService
from bot.domain.services.transfermarkt.service import TransfermarktService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class FootballTeamCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='time',
            options=[
                OptionDef(name='top', pattern=r'top\d+'),
                OptionDef(name='liga', values=LEAGUE_CODES),
            ],
            flags=['full', Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD, Platform.TELEGRAM],
        )

    @property
    def menu_description(self) -> str:
        return 'Time aleatório com tabela ao vivo. Use -full para escalação com imagem do campo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'full' in parsed.flags:
            return await self._full_team(data, parsed)
        return await self._random_team(data, parsed)

    async def _random_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        top_str = parsed.options.get('top', '')

        if top_str and not liga_code:
            try:
                top_n = int(top_str[3:])
            except ValueError:
                top_n = 0
            return await self._global_top_team(data, top_n)

        effective_liga = liga_code or random.choice(LEAGUE_CODES)  # noqa: S311
        league = LEAGUES[effective_liga]

        squad_values, standings, sports_teams = await asyncio.gather(
            TransfermarktService.fetch_squad_values(league),
            TransfermarktService.fetch_standings(league),
            TheSportsDBService.get_teams(league),
        )

        clubs = list(squad_values.values())
        if not clubs:
            logger.warning('squad_values_empty', league=league.tm_id)
            return [Reply.to(data).text('Nenhum time encontrado. Tente novamente! ⚽')]

        if top_str and standings:
            try:
                top_n = int(top_str[3:])
            except ValueError:
                top_n = 0
            if top_n > 0:
                top_ids = {cid for cid, rank in standings.items() if rank <= top_n}
                filtered = [c for c in clubs if c.club_id in top_ids]
                if filtered:
                    clubs = filtered

        club = random.choice(clubs)  # noqa: S311
        rank = standings.get(club.club_id)
        sports_team: SportsDBTeam | None = TheSportsDBService.find_best_match(
            club.name, sports_teams
        )
        caption = TeamCaptionBuilder.build(club, sports_team, league, rank, global_rank=None)

        buffer = await HttpClient.get_buffer(club.badge_url, headers=TransfermarktService.HEADERS)
        return [Reply.to(data).image_buffer(buffer, caption)]

    async def _global_top_team(self, data: CommandData, top_n: int) -> list[BotMessage]:
        top_club = await GlobalTopTeam.fetch(top_n)
        if not top_club:
            return [
                Reply.to(data).text('Não foi possível buscar ranking global. Tente novamente! ⚽')
            ]

        league_code = GlobalTopTeam.find_league(top_club)
        if league_code is None:
            return await self._global_top_bare(data, top_club)

        league = LEAGUES[league_code]
        squad_values, standings, sports_teams = await asyncio.gather(
            TransfermarktService.fetch_squad_values(league),
            TransfermarktService.fetch_standings(league),
            TheSportsDBService.get_teams(league),
        )

        club = squad_values.get(top_club.club_id)
        if club is None:
            return await self._global_top_bare(data, top_club, league=league)

        rank = standings.get(club.club_id)
        sports_team: SportsDBTeam | None = TheSportsDBService.find_best_match(
            club.name, sports_teams
        )
        caption = TeamCaptionBuilder.build(
            club, sports_team, league, rank, global_rank=top_club.rank
        )
        buffer = await HttpClient.get_buffer(club.badge_url, headers=TransfermarktService.HEADERS)
        return [Reply.to(data).image_buffer(buffer, caption)]

    async def _global_top_bare(
        self, data: CommandData, club: TmClub, league: LeagueInfo | None = None
    ) -> list[BotMessage]:
        ts_team: SportsDBTeam | None = await TheSportsDBService.search_team(club.name)

        badge: bytes = b''
        if club.badge_url:
            badge = await HttpClient.get_buffer(
                club.badge_url, headers=TransfermarktService.HEADERS
            )
        elif ts_team and ts_team.badge_url:
            badge = await HttpClient.get_buffer(ts_team.badge_url)

        caption = TeamCaptionBuilder.build_bare(club, ts_team, league)
        return [Reply.to(data).image_buffer(badge, caption)]

    async def _full_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        formation = random_formation()
        top_str = parsed.options.get('top', '')
        try:
            top_n = int(top_str[3:]) if top_str else 0
        except ValueError:
            top_n = 0

        field_image, caption = await FullLineupBuilder.build(liga_code, formation, top_n)
        return [Reply.to(data).image_buffer(field_image, caption)]
