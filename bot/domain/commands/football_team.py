"""Random football team with league standings and optional full lineup image."""

import asyncio
import contextlib
import random

import anyio
import structlog

from bot.data.football import LEAGUE_CODES, LEAGUES, LEAGUES_BY_TM_ID, LeagueInfo
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
from bot.domain.models.football import SportsDBTeam, TmClub, TmPlayer
from bot.domain.models.message import BotMessage
from bot.domain.services.football_field.player_renderer import build_football_field
from bot.domain.services.lineup_builder import LineupBuilder
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
            top_n = int(top_str[3:])
            top_ids = {cid for cid, rank in standings.items() if rank <= top_n}
            filtered = [c for c in clubs if c.club_id in top_ids]
            if filtered:
                clubs = filtered

        club = random.choice(clubs)  # noqa: S311
        rank = standings.get(club.club_id)
        sports_team = TheSportsDBService.find_best_match(club.name, sports_teams)
        caption = TeamCaptionBuilder.build(club, sports_team, league, rank, global_rank=None)

        buffer = await HttpClient.get_buffer(club.badge_url, headers=TransfermarktService.HEADERS)
        return [Reply.to(data).image_buffer(buffer, caption)]

    async def _global_top_team(self, data: CommandData, top_n: int) -> list[BotMessage]:
        top_clubs = await TransfermarktService.fetch_top_clubs(top_n)
        if not top_clubs:
            return [
                Reply.to(data).text('Não foi possível buscar ranking global. Tente novamente! ⚽')
            ]

        top_club = random.choice(top_clubs)  # noqa: S311
        league = LEAGUES_BY_TM_ID.get(top_club.league_tm_id)

        if league is None:
            return await self._global_top_bare(data, top_club)

        squad_values, standings, sports_teams = await asyncio.gather(
            TransfermarktService.fetch_squad_values(league),
            TransfermarktService.fetch_standings(league),
            TheSportsDBService.get_teams(league),
        )

        club = squad_values.get(top_club.club_id)
        if club is None:
            return await self._global_top_bare(data, top_club, league=league)

        rank = standings.get(club.club_id)
        sports_team = TheSportsDBService.find_best_match(club.name, sports_teams)
        caption = TeamCaptionBuilder.build(
            club, sports_team, league, rank, global_rank=top_club.rank
        )
        buffer = await HttpClient.get_buffer(club.badge_url, headers=TransfermarktService.HEADERS)
        return [Reply.to(data).image_buffer(buffer, caption)]

    async def _global_top_bare(
        self, data: CommandData, club: TmClub, league: LeagueInfo | None = None
    ) -> list[BotMessage]:
        ts_team = await TheSportsDBService.search_team(club.name)

        badge: bytes = b''
        if club.badge_url:
            badge = await HttpClient.get_buffer(
                club.badge_url, headers=TransfermarktService.HEADERS
            )
        elif ts_team and ts_team.badge_url:
            badge = await HttpClient.get_buffer(ts_team.badge_url)

        caption = self._build_bare_caption(club, ts_team, league)
        return [Reply.to(data).image_buffer(badge, caption)]

    async def _full_team(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        league = LEAGUES.get(liga_code) if liga_code else None
        formation = random_formation()
        top_str = parsed.options.get('top', '')

        if league:
            all_players = await TransfermarktService.fetch_league_full_squad(league)
            ordered = LineupBuilder.from_league_squad(all_players, formation)
        else:
            top_n: int | None = int(top_str[3:]) if top_str else None
            max_pages = TransfermarktService.POSITION_MAX_PAGES
            if top_n:
                max_pages = max(
                    1,
                    min(
                        (top_n + TransfermarktService.PLAYERS_PER_PAGE - 1)
                        // TransfermarktService.PLAYERS_PER_PAGE,
                        TransfermarktService.GLOBAL_MAX_PAGES,
                    ),
                )
            ordered = await LineupBuilder.from_position_queries(formation, max_pages, top_n)

        photos_ordered, badge_images = await self._fetch_assets(ordered)

        names = [p.name if p else '' for p in ordered]
        flag_emojis: list[str | None] = [
            (p.nationality_flag_emoji if p and p.nationality_flag_emoji else None) for p in ordered
        ]
        overlays: list[tuple[str | None, bytes | None]] = list(
            zip(flag_emojis, badge_images, strict=False)
        )
        total_value = TransfermarktService.sum_market_values(ordered)
        field_image = await asyncio.to_thread(
            build_football_field, photos_ordered, names, formation, overlays, total_value
        )

        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        if total_value:
            caption += f'\n💰 {total_value}'
        return [Reply.to(data).image_buffer(field_image, caption)]

    @staticmethod
    async def _fetch_assets(
        ordered: list[TmPlayer | None],
    ) -> tuple[list[bytes | None], list[bytes | None]]:
        n = len(ordered)
        photos: list[bytes | None] = [None] * n
        badges: list[bytes | None] = [None] * n

        async def _get(url: str) -> bytes | None:
            with contextlib.suppress(Exception):
                return await HttpClient.get_buffer(url, headers=TransfermarktService.HEADERS)
            return None

        async def _fetch_player(i: int, player: TmPlayer) -> None:
            if player.photo_url:
                photos[i] = await _get(player.photo_url)
            if player.badge_url:
                badges[i] = await _get(player.badge_url)

        async with anyio.create_task_group() as tg:
            for i, player in enumerate(ordered):
                if player:
                    tg.start_soon(_fetch_player, i, player)

        return photos, badges

    @staticmethod
    def _build_bare_caption(
        club: TmClub, ts_team: SportsDBTeam | None, league: LeagueInfo | None
    ) -> str:
        country = ts_team.country if ts_team else (league.country if league else club.country)
        founded = ts_team.founded if ts_team else ''
        name = ts_team.name if ts_team else club.name
        title = f'*{name}*' if league is None else f'*{name}* — {league.name}'
        flag = league.flag if league else '🌍'
        head = f'\n{flag} {country}' if country else f'\n{flag}'
        if founded:
            head += f'   📅 {founded}'
        lines = [title, head]
        if ts_team and ts_team.stadium:
            lines.append(f'🏟️ {ts_team.stadium}')
            if ts_team.capacity:
                try:
                    cap = f'{int(ts_team.capacity):,}'.replace(',', '.')
                except ValueError:
                    cap = ts_team.capacity
                lines.append(f'💺 {cap} lugares')
        lines.append(f'🏆 #{club.rank}º mais valioso')
        if club.squad_value:
            lines.append(f'💰 {club.squad_value}')
        return '\n'.join(lines)
