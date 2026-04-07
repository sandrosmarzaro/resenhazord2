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
from bot.domain.models.message import BotMessage
from bot.domain.services.transfermarkt import TmPlayer, TransfermarktService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

# Portuguese and English label keys from Transfermarkt player profile
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

        default_max = TransfermarktService.LEAGUE_MAX_PAGES  # top 100 globally or per-league

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

        details: dict[str, str] = {}
        if player.profile_url:
            try:
                details = await TransfermarktService.fetch_player_profile(player.profile_url)
            except Exception:  # noqa: BLE001
                logger.warning('player_profile_fetch_failed', url=player.profile_url)

        caption = self._build_caption(player, league, details)
        buffer = await HttpClient.get_buffer(player.photo_url, headers=TransfermarktService.HEADERS)
        return [Reply.to(data).image_buffer(buffer, caption)]

    @staticmethod
    def _build_caption(player: TmPlayer, league: LeagueInfo | None, details: dict[str, str]) -> str:
        club_flag = league.flag if league else ''

        foot = next((details[k] for k in _FOOT_KEYS if k in details), '').capitalize()
        height = next((details[k] for k in _HEIGHT_KEYS if k in details), '')
        other_pos = next((details[k] for k in _OTHER_POS_KEYS if k in details), '')
        born_country = next((details[k] for k in _BORN_COUNTRY_KEYS if k in details), '')
        born_city = next((details[k] for k in _BORN_CITY_KEYS if k in details), '')

        lines = [
            f'*{player.name}* — {player.position}',
            '',
            f'🎂 {player.age} anos   {player.nationality_flag_emoji} {player.nationality}',
        ]
        if born_city or born_country:
            born_flag = nationality_flag(born_country) if born_country else ''
            parts = [born_city, born_country] if born_country and born_country != born_city else [
                born_city or born_country
            ]
            display = ', '.join(p for p in parts if p)
            prefix = born_flag or '📍'
            lines.append(f'{prefix} {display}'.strip())
        lines.append(f'🏟️ {player.club} {club_flag}')
        if height or foot:
            info = f'📏 {height}' if height else ''
            if foot:
                info += f'   👟 {foot}' if info else f'👟 {foot}'
            lines.append(info)
        if other_pos:
            lines.append(f'🔄 {other_pos}')
        lines.extend(['', f'💰 {player.market_value}'])
        return '\n'.join(lines)
