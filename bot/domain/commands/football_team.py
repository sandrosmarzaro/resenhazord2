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

        role_pool = await self._fetch_role_pools(formation, league)
        ordered = self._assign_to_slots(formation, role_pool)
        photos_ordered = await self._fetch_photos(ordered)

        names = [p.name if p else '' for p in ordered]
        flags = [p.nationality_flag_emoji if p else None for p in ordered]
        field_image = build_football_field(photos_ordered, names, formation, flags)

        total_value = _sum_market_values(ordered)
        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        if total_value:
            caption += f'\n💰 {total_value}'
        return [Reply.to(data).image_buffer(field_image, caption)]

    @staticmethod
    async def _fetch_role_pools(
        formation: Formation,
        league: LeagueInfo | None,
    ) -> dict[str, list[TmPlayer]]:
        max_pages = (
            TransfermarktService.LEAGUE_MAX_PAGES
            if league
            else TransfermarktService.POSITION_MAX_PAGES
        )
        unique_roles = list({slot.role for slot in formation.slots})

        # For each role, pick 2 random pages to fetch concurrently
        role_page_pairs = [
            (role, page)
            for role in unique_roles
            for page in random.sample(range(1, max_pages + 1), min(2, max_pages))
        ]

        results = await asyncio.gather(
            *[
                TransfermarktService.fetch_page_by_role(role, page, league)
                for role, page in role_page_pairs
            ]
        )

        role_pool: dict[str, list[TmPlayer]] = {role: [] for role in unique_roles}
        for (role, _), players in zip(role_page_pairs, results, strict=False):
            role_pool[role].extend(players)

        for role in unique_roles:
            seen: set[str] = set()
            deduped = [p for p in role_pool[role] if not (p.name in seen or seen.add(p.name))]  # type: ignore[func-returns-value]
            random.shuffle(deduped)
            role_pool[role] = deduped

        return role_pool

    @staticmethod
    def _assign_to_slots(
        formation: Formation,
        role_pool: dict[str, list[TmPlayer]],
    ) -> list[TmPlayer | None]:
        pool = {role: list(players) for role, players in role_pool.items()}
        ordered: list[TmPlayer | None] = []
        for slot in formation.slots:
            slot_pool = pool.get(slot.role, [])
            ordered.append(slot_pool.pop(0) if slot_pool else None)
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
