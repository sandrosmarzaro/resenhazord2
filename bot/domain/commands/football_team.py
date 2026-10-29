"""Random football team with league standings and optional full lineup image."""

import asyncio
import random
from typing import ClassVar

import httpx
import structlog

from bot.data.football import LEAGUES, LEAGUES_BY_TM_ID, MARKET_LEAGUE_CODES, LeagueInfo
from bot.data.football_formations import random_formation
from bot.data.market_dataset import SEASON_FOOTER
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
from bot.domain.models.football import SportsDBTeam, TmSquadStats
from bot.domain.models.message import BotMessage
from bot.domain.services.espn import EspnService
from bot.domain.services.full_lineup_builder import FullLineupBuilder
from bot.domain.services.market_dataset import MarketDataset
from bot.domain.services.team_caption_builder import TeamCaptionBuilder
from bot.domain.services.team_name_matcher import TeamNameMatcher
from bot.domain.services.thesportsdb import TheSportsDBService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class FootballTeamCommand(Command):
    _NO_RANK: ClassVar[tuple[int, str]] = (0, '')

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='time',
            options=[
                OptionDef(name='top', pattern=r'top\s?\d+'),
                OptionDef(name='liga', values=MARKET_LEAGUE_CODES),
            ],
            flags=['full', 'fifa', Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return (
            'Time aleatório com valor de elenco e posição na tabela. '
            'Use full para escalação e fifa para um time com os ratings do EA FC.'
        )

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'fifa' in parsed.flags:
            return await self._fifa_team(data, parsed)
        if 'full' in parsed.flags:
            return await self._full_team(data, parsed)
        return await self._random_team(data, parsed)

    async def _random_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        top_n = parsed.number('top')
        if top_n > 0 and not liga_code:
            return await self._global_top_team(data, top_n)

        league = LEAGUES[liga_code or random.choice(MARKET_LEAGUE_CODES)]
        clubs, table = await self._league_data(league)
        if not clubs:
            return [Reply.to(data).text('Não achei esse time. Tenta de novo! ⚽')]

        ranked = [club for club in clubs if 0 < table.get(club.club_id, self._NO_RANK)[0] <= top_n]
        club = random.choice(ranked or clubs)
        caption = await self._caption(club, league, table.get(club.club_id))
        return await self._reply(data, club, caption)

    async def _global_top_team(self, data: CommandData, top_n: int) -> list[BotMessage]:
        clubs = await MarketDataset.clubs()
        club = random.choice(clubs[:top_n])
        league = LEAGUES_BY_TM_ID.get(club.league_id)
        table = (await self._league_data(league))[1] if league else {}
        global_rank = clubs.index(club) + 1
        caption = await self._caption(club, league, table.get(club.club_id), global_rank)
        return await self._reply(data, club, caption)

    @staticmethod
    async def _league_data(
        league: LeagueInfo,
    ) -> tuple[list[TmSquadStats], dict[str, tuple[int, str]]]:
        clubs, standings = await asyncio.gather(
            MarketDataset.clubs(league.tm_id),
            EspnService.fetch_standings(league),
        )
        rank_by_team = {row.team: row.rank for row in standings}
        pairs = TeamNameMatcher.pair([club.name for club in clubs], list(rank_by_team))
        table = {
            club.club_id: (rank_by_team[pairs[club.name]], pairs[club.name])
            for club in clubs
            if club.name in pairs
        }
        return clubs, table

    @classmethod
    async def _caption(
        cls,
        club: TmSquadStats,
        league: LeagueInfo | None,
        table_entry: tuple[int, str] | None,
        global_rank: int | None = None,
    ) -> str:
        rank, short_name = table_entry or (None, club.name)
        sports_team = await cls._sports_team(short_name)
        caption = TeamCaptionBuilder.build(club, sports_team, league, rank, global_rank)
        return f'{caption}\n{SEASON_FOOTER.format(season=await MarketDataset.season())}'

    @staticmethod
    async def _sports_team(name: str) -> SportsDBTeam | None:
        # Stadium and founding year are extras; TheSportsDB's free key rate-limits hard.
        try:
            return await TheSportsDBService.search_team(name)
        except httpx.HTTPError as error:
            logger.warning('upstream_failed', upstream='thesportsdb', team=name, error=str(error))
            return None

    @staticmethod
    async def _reply(data: CommandData, club: TmSquadStats, caption: str) -> list[BotMessage]:
        buffer = await HttpClient.get_buffer(club.badge_url)
        return [Reply.to(data).image_buffer(buffer, caption)]

    async def _full_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        formation = random_formation()
        top_n = parsed.number('top')

        field_image, caption = await FullLineupBuilder.build(liga_code, formation, top_n)
        return [Reply.to(data).image_buffer(field_image, caption)]

    async def _fifa_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if parsed.options.get('liga'):
            reply = 'O time FIFA ainda não filtra por liga. Usa *,time fifa*! ⚽'
            return [Reply.to(data).text(reply)]
        top_n = parsed.number('top')
        field_image, caption = await FullLineupBuilder.build_fifa(random_formation(), top_n)
        return [Reply.to(data).image_buffer(field_image, caption)]
