"""Random football player from Transfermarkt's most-valuable rankings."""

import random

import structlog

from bot.data.football import LEAGUE_CODES, LEAGUES, LeagueInfo
from bot.data.nationality_flags import nationality_flag
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
from bot.domain.models.football import TmPlayer
from bot.domain.models.message import BotMessage
from bot.domain.services.transfermarkt.service import TransfermarktService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class FootballPlayerCommand(Command):
    _FOOT_KEYS = ('Pé', 'Foot')
    _HEIGHT_KEYS = ('Altura', 'Height')
    _OTHER_POS_KEYS = (
        'Posições secundárias',
        'Posição secundária',
        'Other positions',
        'Other position',
        'Secondary positions',
    )
    _BORN_COUNTRY_KEYS = ('País de nascimento', 'Country of birth')
    _BORN_CITY_KEYS = ('Local de nascimento', 'Place of birth')

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
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Jogador aleatório do top de mais valiosos. Use --liga <código> e top<N>.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        liga_code = parsed.options.get('liga')
        league = LEAGUES.get(liga_code) if liga_code else None
        top_str = parsed.options.get('top', '')

        max_page = self._resolve_max_page(top_str, league)
        page = random.randint(1, max_page)  # noqa: S311
        players = await TransfermarktService.fetch_page(page, league)

        if top_str and players and page == max_page:
            players = self._trim_last_page(players, top_str, max_page)

        if not players:
            return [Reply.to(data).text('Nenhum jogador encontrado. Tente novamente! ⚽')]

        player = random.choice(players)  # noqa: S311
        details = await self._fetch_details(player.profile_url)
        caption = self._build_caption(player, league, details)
        buffer = await HttpClient.get_buffer(player.photo_url, headers=TransfermarktService.HEADERS)
        return [Reply.to(data).image_buffer(buffer, caption)]

    def _resolve_max_page(self, top_str: str, league: LeagueInfo | None) -> int:
        default_max = (
            TransfermarktService.LEAGUE_MAX_PAGES
            if league
            else TransfermarktService.GLOBAL_MAX_PAGES
        )
        if not top_str:
            return default_max
        try:
            top_n = int(top_str[3:])
        except ValueError:
            return default_max
        if top_n <= 0:
            return default_max
        pages_for_top = (
            top_n + TransfermarktService.PLAYERS_PER_PAGE - 1
        ) // TransfermarktService.PLAYERS_PER_PAGE
        return max(1, min(pages_for_top, default_max))

    @staticmethod
    def _trim_last_page(players: list[TmPlayer], top_str: str, max_page: int) -> list[TmPlayer]:
        try:
            top_n = int(top_str[3:])
        except ValueError:
            return players
        items_on_last_page = top_n - (max_page - 1) * TransfermarktService.PLAYERS_PER_PAGE
        return players[:items_on_last_page]

    @staticmethod
    async def _fetch_details(profile_url: str) -> dict[str, str]:
        if not profile_url:
            return {}
        try:
            return await TransfermarktService.fetch_player_profile(profile_url)
        except Exception:  # noqa: BLE001
            logger.warning('player_profile_fetch_failed', url=profile_url)
            return {}

    @classmethod
    def _build_caption(
        cls, player: TmPlayer, league: LeagueInfo | None, details: dict[str, str]
    ) -> str:
        club_flag = league.flag if league else ''
        foot = cls._lookup(details, cls._FOOT_KEYS).capitalize()
        height = cls._lookup(details, cls._HEIGHT_KEYS)
        other_pos = cls._lookup(details, cls._OTHER_POS_KEYS)
        born_country = cls._lookup(details, cls._BORN_COUNTRY_KEYS)
        born_city = cls._lookup(details, cls._BORN_CITY_KEYS)

        lines: list[str] = [
            f'*{player.name}* — {player.position}',
            '',
            f'🎂 {player.age} anos   {player.nationality_flag_emoji} {player.nationality}',
        ]
        lines.extend(cls._birth_line(born_city, born_country))
        lines.append(f'🏟️ {player.club} {club_flag}')
        lines.extend(cls._physical_line(height, foot))
        if other_pos:
            lines.append(f'🔄 {other_pos}')
        lines.extend(['', f'💰 {player.market_value}'])
        return '\n'.join(lines)

    @staticmethod
    def _lookup(details: dict[str, str], keys: tuple[str, ...]) -> str:
        return next((details[k] for k in keys if k in details), '')

    @classmethod
    def _birth_line(cls, born_city: str, born_country: str) -> list[str]:
        if not born_city and not born_country:
            return []
        born_flag = nationality_flag(born_country) if born_country else ''
        parts = (
            [born_city, born_country]
            if born_country and born_country != born_city
            else [born_city or born_country]
        )
        display = ', '.join(p for p in parts if p)
        prefix = born_flag or '📍'
        return [f'{prefix} {display}'.strip()]

    @staticmethod
    def _physical_line(height: str, foot: str) -> list[str]:
        if not height and not foot:
            return []
        if height and foot:
            return [f'📏 {height}   👟 {foot}']
        return [f'📏 {height}' if height else f'👟 {foot}']
