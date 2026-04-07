"""Random football team with league standings and optional full lineup image."""

import asyncio
import contextlib
import random
import re

import anyio
import structlog

from bot.data.football import LEAGUE_CODES, LEAGUES, LeagueInfo
from bot.data.football_formations import Formation, random_formation
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
from bot.domain.services.football_field_builder import build_football_field
from bot.domain.services.thesportsdb import SportsDBTeam, StandingRow, TheSportsDBService
from bot.domain.services.transfermarkt import TmPlayer, TmSquadStats, TransfermarktService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

_VALUE_RE = re.compile(r'€\s*([\d.,]+)\s*(mi\.|mil\.)')


def _parse_market_value_millions(value_str: str) -> float:
    m = _VALUE_RE.search(value_str)
    if not m:
        return 0.0
    number_str = m.group(1).replace('.', '').replace(',', '.')
    try:
        number = float(number_str)
    except ValueError:
        return 0.0
    return number / 1000 if m.group(2) == 'mil.' else number


def _sum_market_values(players: list[TmPlayer | None]) -> str | None:
    total = sum(
        _parse_market_value_millions(p.market_value) for p in players if p and p.market_value
    )
    if total <= 0:
        return None
    us = f'{total:,.2f}'
    br = us.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'€ {br} mi.'


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
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
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
            return await self._global_top_team(data, int(top_str[3:]))

        effective_liga = liga_code or random.choice(LEAGUE_CODES)  # noqa: S311
        league = LEAGUES[effective_liga]

        teams, standings, squad_values = await asyncio.gather(
            TheSportsDBService.get_teams(league),
            TheSportsDBService.get_standings(league),
            TransfermarktService.fetch_squad_values(league),
        )

        if not squad_values:
            logger.warning('squad_values_empty', league=league.tm_id)

        if not teams:
            return [Reply.to(data).text('Nenhum time encontrado. Tente novamente! ⚽')]

        if top_str and standings:
            top_n = int(top_str[3:])
            top_names = {r.team.lower() for r in standings[:top_n]}
            filtered = [t for t in teams if t.name.lower() in top_names]
            if filtered:
                teams = filtered

        team = random.choice(teams)  # noqa: S311
        rank = self._find_rank(team.name, standings)
        squad_stats = self._find_squad_stats(team.name, squad_values)
        caption = self._build_team_caption(team, league.name, league.flag, rank, squad_stats)

        buffer = await HttpClient.get_buffer(team.badge_url)
        return [Reply.to(data).image_buffer(buffer, caption)]

    async def _global_top_team(self, data: CommandData, top_n: int) -> list[BotMessage]:
        clubs = await TransfermarktService.fetch_top_clubs(top_n)
        if not clubs:
            return [Reply.to(data).text(
                'Não foi possível buscar ranking global. Tente novamente! ⚽'
            )]

        club = random.choice(clubs)  # noqa: S311
        ts_team = await TheSportsDBService.search_team(club.name)

        badge: bytes = b''
        if club.badge_url:
            badge = await HttpClient.get_buffer(club.badge_url)
        elif ts_team and ts_team.badge_url:
            badge = await HttpClient.get_buffer(ts_team.badge_url)

        country = ts_team.country if ts_team else club.country
        founded = ts_team.founded if ts_team else ''
        name = ts_team.name if ts_team else club.name

        lines = [f'*{name}*', f'\n🌍 {country}']
        if founded:
            lines[1] += f'   📅 {founded}'
        lines.append(f'📊 #{club.rank}º mais valioso')
        if club.squad_value:
            lines.append(f'💰 {club.squad_value}')

        return [Reply.to(data).image_buffer(badge, '\n'.join(lines))]

    async def _full_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        league = LEAGUES.get(liga_code) if liga_code else None
        formation = random_formation()

        all_players = await self._fetch_players(league)
        ordered = self._pick_lineup(all_players, formation)
        photos_ordered = await self._fetch_photos(ordered)

        names = [p.name if p else '' for p in ordered]
        flags = [p.nationality_flag_emoji if p else None for p in ordered]
        total_value = _sum_market_values(ordered)
        field_image = build_football_field(photos_ordered, names, formation, flags, total_value)

        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        if total_value:
            caption += f'\n💰 {total_value}'
        return [Reply.to(data).image_buffer(field_image, caption)]

    @staticmethod
    async def _fetch_players(league: LeagueInfo | None) -> list[TmPlayer]:
        if league:
            pages = list(range(1, TransfermarktService.LEAGUE_MAX_PAGES + 1))
        else:
            pages = random.sample(
                range(1, TransfermarktService.GLOBAL_MAX_PAGES + 1),
                min(10, TransfermarktService.GLOBAL_MAX_PAGES),
            )

        results = await asyncio.gather(
            *[TransfermarktService.fetch_page(page, league) for page in pages]
        )

        seen: set[str] = set()
        all_players: list[TmPlayer] = []
        for players in results:
            for p in players:
                if p.name not in seen:
                    seen.add(p.name)
                    all_players.append(p)
        random.shuffle(all_players)
        return all_players

    @staticmethod
    def _pick_lineup(players: list[TmPlayer], formation: Formation) -> list[TmPlayer | None]:
        pools: dict[str, list[TmPlayer]] = {'GK': [], 'DEF': [], 'MID': [], 'ATT': []}
        for p in players:
            role = TransfermarktService.POSITION_ROLES.get(p.position)
            if role:
                pools[role].append(p)

        used: set[str] = set()
        ordered: list[TmPlayer | None] = []
        for slot in formation.slots:
            slot_pool = pools.get(slot.role, [])
            player = next((p for p in slot_pool if p.name not in used), None)
            if player:
                used.add(player.name)
            ordered.append(player)
        return ordered

    @staticmethod
    async def _fetch_photos(ordered: list[TmPlayer | None]) -> list[bytes | None]:
        photos: list[bytes | None] = [None] * len(ordered)

        async def _fetch(i: int, player: TmPlayer) -> None:
            with contextlib.suppress(Exception):
                photos[i] = await HttpClient.get_buffer(
                    player.photo_url, headers=TransfermarktService.HEADERS
                )

        async with anyio.create_task_group() as tg:
            for i, player in enumerate(ordered):
                if player:
                    tg.start_soon(_fetch, i, player)

        return photos

    @staticmethod
    def _find_rank(team_name: str, standings: list[StandingRow]) -> int | None:
        name_lower = team_name.lower()
        return next((r.rank for r in standings if r.team.lower() == name_lower), None)

    @staticmethod
    def _find_squad_stats(
        team_name: str, squad_values: dict[str, TmSquadStats]
    ) -> TmSquadStats | None:
        name_lower = team_name.lower()
        if name_lower in squad_values:
            return squad_values[name_lower]
        name_words = set(name_lower.split())
        for key, val in squad_values.items():
            if name_words & set(key.split()):
                return val
        return None

    @staticmethod
    def _format_capacity(raw: str) -> str:
        try:
            return f'{int(raw):,}'.replace(',', '.')
        except ValueError:
            return raw

    @staticmethod
    def _build_team_caption(
        team: SportsDBTeam,
        league_name: str,
        league_flag: str,
        rank: int | None,
        squad_stats: TmSquadStats | None,
    ) -> str:
        lines = [
            f'*{team.name}* — {league_name}',
            f'\n{league_flag} {team.country}   📅 {team.founded}',
        ]
        if team.stadium:
            lines.append(f'🏟️ {team.stadium}')
            if team.capacity:
                cap = FootballTeamCommand._format_capacity(team.capacity)
                lines.append(f'💺 {cap} lugares')
        if rank:
            lines.append(f'📊 {rank}º na tabela')
        if squad_stats:
            if squad_stats.squad_size:
                squad_line = f'👥 {squad_stats.squad_size} jogadores'
                if squad_stats.avg_age:
                    squad_line += f'   ⌀ {squad_stats.avg_age} anos'
                lines.append(squad_line)
            if squad_stats.foreigners_count:
                foreign_line = f'🌍 {squad_stats.foreigners_count} estrangeiros'
                if squad_stats.foreigners_pct:
                    foreign_line += f' ({squad_stats.foreigners_pct}%)'
                lines.append(foreign_line)
            if squad_stats.market_value:
                lines.append(f'💰 {squad_stats.market_value}')
        return '\n'.join(lines)
