"""Random football player from the most-valuable rankings."""

import random
from typing import ClassVar

from bot.data.football import LEAGUES, MARKET_LEAGUE_CODES, LeagueInfo
from bot.data.nationality_flags import nationality_flag
from bot.data.transfermarkt_positions import FOOT_LABELS, POSITION_LABELS
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
from bot.domain.models.football import PlayerProfile, TmPlayer
from bot.domain.models.message import BotMessage
from bot.domain.services.market_dataset import MarketDataset
from bot.infrastructure.http_client import HttpClient


class FootballPlayerCommand(Command):
    GLOBAL_POOL: ClassVar[int] = 1000
    LEAGUE_POOL: ClassVar[int] = 100
    _CENTIMETERS_PER_METER: ClassVar[int] = 100

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='jogador',
            options=[
                OptionDef(name='top', pattern=r'top\d+'),
                OptionDef(name='liga', values=MARKET_LEAGUE_CODES),
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
        league = LEAGUES[liga_code] if liga_code else None
        players = await MarketDataset.players(league.tm_id if league else '')
        pool = players[: self._pool_size(parsed.options.get('top', ''), league)]

        if not pool:
            return [Reply.to(data).text('Não achei esse jogador. Tenta de novo! ⚽')]

        player = random.choice(pool)
        caption = self._build_caption(player, league)
        buffer = await HttpClient.get_buffer(player.photo_url)
        return [Reply.to(data).image_buffer(buffer, caption)]

    def _pool_size(self, top_str: str, league: LeagueInfo | None) -> int:
        top_n = int(top_str[3:]) if top_str else 0
        if top_n > 0:
            return top_n
        return self.LEAGUE_POOL if league else self.GLOBAL_POOL

    @classmethod
    def _build_caption(cls, player: TmPlayer, league: LeagueInfo | None) -> str:
        club_flag = league.flag if league else ''
        position = POSITION_LABELS.get(player.position, player.position)
        lines: list[str] = [
            f'*{player.name}* — {position}',
            '',
            f'🎂 {player.age} anos   {player.nationality_flag_emoji} {player.nationality}',
        ]
        lines.extend(cls._birth_line(player.profile))
        lines.append(f'🏟️ {player.club} {club_flag}')
        lines.extend(cls._physical_line(player.profile))
        lines.extend(['', f'💰 {MarketDataset.format_euros(player.market_value)}'])
        return '\n'.join(lines)

    @staticmethod
    def _birth_line(profile: PlayerProfile) -> list[str]:
        city, country = profile.birth_city, profile.birth_country
        if not city and not country:
            return []
        parts = [city, country] if country and country != city else [city or country]
        display = ', '.join(part for part in parts if part)
        prefix = nationality_flag(country) or '📍'
        return [f'{prefix} {display}']

    @classmethod
    def _physical_line(cls, profile: PlayerProfile) -> list[str]:
        height = cls._height(profile.height_cm)
        foot = FOOT_LABELS.get(profile.foot, '')
        if height and foot:
            return [f'📏 {height}   👟 {foot}']
        if height or foot:
            return [f'📏 {height}' if height else f'👟 {foot}']
        return []

    @classmethod
    def _height(cls, height_cm: str) -> str:
        if not height_cm:
            return ''
        meters = int(float(height_cm)) / cls._CENTIMETERS_PER_METER
        return f'{meters:.2f} m'.replace('.', ',')
