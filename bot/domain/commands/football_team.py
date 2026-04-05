"""Random football team with league standings and optional full lineup image."""

import asyncio
import contextlib
import random

import anyio
import structlog

from bot.data.football import LEAGUE_CODES, LEAGUES
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
from bot.domain.services.transfermarkt import TmPlayer, TransfermarktService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

_POSITION_ROLES: dict[str, list[str]] = {
    'GK': ['Goleiro', 'Guarda-Redes', 'Goalkeeper', 'Porteiro'],
    'DEF': [
        'Zagueiro', 'Lateral Dir.', 'Lateral Esq.',
        'Defensor Central', 'Lateral Direito', 'Lateral Esquerdo',
        'Centre-Back', 'Left-Back', 'Right-Back',
        'Defensor', 'Libero',
    ],
    'MID': [
        'Volante', 'Meia Central', 'Meia Ofensivo',
        'Meia-Esquerda', 'Meia-Direita', 'Meio-Campo',
        'Medio Defensivo', 'Medio Central', 'Medio Ofensivo',
        'Defensive Midfield', 'Central Midfield', 'Attacking Midfield',
        'Left Midfield', 'Right Midfield',
        'Segundo Atacante',
    ],
    'ATT': [
        'Centroavante', 'Ponta Direita', 'Ponta Esquerda',
        'Atacante', 'Segunda Ponta', 'Extremo Direito', 'Extremo Esquerdo',
        'Centre-Forward', 'Left Winger', 'Right Winger',
        'Second Striker',
    ],
}


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
        liga_code = parsed.options.get('liga') or random.choice(LEAGUE_CODES)  # noqa: S311
        league = LEAGUES[liga_code]
        top_str = parsed.options.get('top', '')

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
        squad_value = self._find_squad_value(team.name, squad_values)
        caption = self._build_team_caption(team, league.name, league.flag, rank, squad_value)

        buffer = await HttpClient.get_buffer(team.badge_url)
        return [Reply.to(data).image_buffer(buffer, caption)]

    async def _full_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        league = LEAGUES.get(liga_code) if liga_code else None
        max_pages = (
            TransfermarktService.LEAGUE_MAX_PAGES
            if league
            else TransfermarktService.GLOBAL_MAX_PAGES
        )
        pages = random.sample(range(1, max_pages + 1), min(2, max_pages))
        results = await asyncio.gather(
            *[TransfermarktService.fetch_page(p, league) for p in pages]
        )
        players = list({p.name: p for result in results for p in result}.values())

        if not players:
            return [Reply.to(data).text('Não foi possível montar a escalação. Tente novamente! ⚽')]

        random.shuffle(players)
        formation = random_formation()
        lineup = self._pick_lineup(players, formation)

        ordered: list[TmPlayer | None] = [
            lineup[slot.role].pop(0) if lineup[slot.role] else None for slot in formation.slots
        ]

        photos_ordered: list[bytes | None] = [None] * len(ordered)
        flags_ordered: list[bytes | None] = [None] * len(ordered)

        async def _fetch_photo(i: int, player: TmPlayer) -> None:
            with contextlib.suppress(Exception):
                photos_ordered[i] = await HttpClient.get_buffer(
                    player.photo_url, headers=TransfermarktService.HEADERS
                )

        async def _fetch_flag(i: int, url: str) -> None:
            with contextlib.suppress(Exception):
                flags_ordered[i] = await HttpClient.get_buffer(
                    url, headers=TransfermarktService.HEADERS
                )

        async with anyio.create_task_group() as tg:
            for i, player in enumerate(ordered):
                if player:
                    tg.start_soon(_fetch_photo, i, player)
                    if player.nationality_flag_url:
                        tg.start_soon(_fetch_flag, i, player.nationality_flag_url)

        names = [p.name if p else '' for p in ordered]
        field_image = build_football_field(photos_ordered, names, formation, flags_ordered)
        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        return [Reply.to(data).image_buffer(field_image, caption)]

    @staticmethod
    def _pick_lineup(
        players: list[TmPlayer], formation: Formation
    ) -> dict[str, list[TmPlayer | None]]:
        slots_needed: dict[str, int] = {}
        for slot in formation.slots:
            slots_needed[slot.role] = slots_needed.get(slot.role, 0) + 1

        remaining = list(players)
        lineup: dict[str, list[TmPlayer | None]] = {role: [] for role in slots_needed}

        # First pass: match players by their actual position
        for role, positions in _POSITION_ROLES.items():
            if role not in slots_needed:
                continue
            matched = [p for p in remaining if p.position in positions]
            take = matched[:slots_needed[role]]
            lineup[role].extend(take)
            for p in take:
                remaining.remove(p)

        # Second pass: fill non-GK slots from remaining pool
        for role, needed in slots_needed.items():
            if role == 'GK':
                continue
            while len(lineup[role]) < needed and remaining:
                lineup[role].append(remaining.pop(0))

        # Pad all slots with None (GK stays None rather than using wrong-position player)
        for role, needed in slots_needed.items():
            while len(lineup[role]) < needed:
                lineup[role].append(None)

        return lineup

    @staticmethod
    def _find_rank(team_name: str, standings: list[StandingRow]) -> int | None:
        name_lower = team_name.lower()
        return next((r.rank for r in standings if r.team.lower() == name_lower), None)

    @staticmethod
    def _find_squad_value(team_name: str, squad_values: dict[str, str]) -> str | None:
        name_lower = team_name.lower()
        if name_lower in squad_values:
            return squad_values[name_lower]
        name_words = set(name_lower.split())
        for key, val in squad_values.items():
            if name_words & set(key.split()):
                return val
        return None

    @staticmethod
    def _build_team_caption(
        team: SportsDBTeam,
        league_name: str,
        league_flag: str,
        rank: int | None,
        squad_value: str | None,
    ) -> str:
        lines = [
            f'*{team.name}* — {league_name}',
            f'\n{league_flag} {team.country}   📅 {team.founded}',
        ]
        if rank:
            lines.append(f'📊 {rank}º na tabela')
        if squad_value:
            lines.append(f'💰 {squad_value}')
        return '\n'.join(lines)
