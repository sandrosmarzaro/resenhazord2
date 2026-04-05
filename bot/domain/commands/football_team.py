"""Random football team with league standings and optional full lineup image."""

import asyncio
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
    'GK': ['Goleiro'],
    'DEF': ['Zagueiro', 'Lateral Dir.', 'Lateral Esq.'],
    'MID': ['Volante', 'Meia Central', 'Meia Ofensivo'],
    'ATT': ['Centroavante', 'Ponta Direita', 'Ponta Esquerda'],
}
_ROLE_SLOTS: dict[str, int] = {'GK': 1, 'DEF': 4, 'MID': 3, 'ATT': 3}


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
        page = random.randint(1, TransfermarktService.GLOBAL_MAX_PAGES)  # noqa: S311
        players = await TransfermarktService.fetch_page(page, league)

        if not players:
            return [Reply.to(data).text('Não foi possível montar a escalação. Tente novamente! ⚽')]

        random.shuffle(players)
        formation = random_formation()
        lineup = self._pick_lineup(players, formation)

        ordered = [
            lineup[slot.role].pop(0) if lineup[slot.role] else None for slot in formation.slots
        ]
        photos = await self._download_photos([p for p in ordered if p])

        photo_map: dict[int, bytes | None] = {}
        photo_idx = 0
        for i, player in enumerate(ordered):
            if player is not None:
                photo_map[i] = photos[photo_idx]
                photo_idx += 1
            else:
                photo_map[i] = None

        photos_ordered = [photo_map.get(i) for i in range(len(ordered))]
        names = [p.name if p else '' for p in ordered]

        field_image = build_football_field(photos_ordered, names, formation)
        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        return [Reply.to(data).image_buffer(field_image, caption)]

    @staticmethod
    async def _download_photos(players: list[TmPlayer]) -> list[bytes | None]:
        results: list[bytes | None] = [None] * len(players)

        async def _fetch(index: int, player: TmPlayer) -> None:
            try:
                results[index] = await HttpClient.get_buffer(
                    player.photo_url, headers=TransfermarktService.HEADERS
                )
            except Exception:  # noqa: BLE001
                results[index] = None

        async with anyio.create_task_group() as tg:
            for i, player in enumerate(players):
                tg.start_soon(_fetch, i, player)

        return results

    @staticmethod
    def _pick_lineup(players: list[TmPlayer], formation: Formation) -> dict[str, list[TmPlayer]]:
        slots_needed: dict[str, int] = {}
        for slot in formation.slots:
            slots_needed[slot.role] = slots_needed.get(slot.role, 0) + 1

        remaining = list(players)
        lineup: dict[str, list[TmPlayer]] = {role: [] for role in slots_needed}

        for role, positions in _POSITION_ROLES.items():
            if role not in slots_needed:
                continue
            needed = slots_needed[role]
            matched = [p for p in remaining if p.position in positions]
            chosen = matched[:needed]
            for p in chosen:
                remaining.remove(p)
            lineup[role] = chosen

        for role, needed in slots_needed.items():
            while len(lineup[role]) < needed and remaining:
                lineup[role].append(remaining.pop(0))

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
        # Partial match fallback
        for key, val in squad_values.items():
            if key in name_lower or name_lower in key:
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
            f'\n{league_flag} {team.country}   📅 Fundado em {team.founded}',
        ]
        if rank:
            lines.append(f'📊 {rank}º na tabela')
        if squad_value:
            lines.append(f'💰 {squad_value}')
        return '\n'.join(lines)
