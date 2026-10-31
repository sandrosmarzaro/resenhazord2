"""Random football player from the most-valuable rankings."""

import random
from typing import ClassVar

from bot.data.football import LEAGUES, MARKET_LEAGUE_CODES, LeagueInfo
from bot.data.market_dataset import SEASON_FOOTER
from bot.data.nationality_flags import nationality_flag, nationality_pt
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
from bot.domain.services.fifa_ratings import FifaRatings
from bot.domain.services.market_dataset import MarketDataset, format_euros
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
                OptionDef(name='top', pattern=r'top\s?\d+'),
                OptionDef(name='liga', values=MARKET_LEAGUE_CODES),
            ],
            flags=['fifa', Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return (
            'Jogador aleatório do top de mais valiosos. Use --liga <código> e top<N>, '
            'ou fifa para uma carta do EA FC.'
        )

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'fifa' in parsed.flags:
            return await self._fifa_card(data, parsed)
        liga_code = parsed.options.get('liga')
        league = LEAGUES[liga_code] if liga_code else None
        players = await MarketDataset.players(league.tm_id if league else '')
        pool = players[: self._pool_size(parsed.number('top'), league)]

        if not pool:
            return [Reply.to(data).text('Não achei esse jogador. Tenta de novo! ⚽')]

        player = random.choice(pool)
        caption = self._build_caption(player, league, await MarketDataset.season())
        buffer = await HttpClient.get_buffer(player.photo_url)
        return [Reply.to(data).image_buffer(buffer, caption)]

    @staticmethod
    async def _fifa_card(data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if parsed.options.get('liga'):
            reply = 'A carta FIFA ainda não filtra por liga. Usa *,jogador fifa*! ⚽'
            return [Reply.to(data).text(reply)]
        players = [player for player in await FifaRatings.top() if player.card_url]
        top_n = parsed.number('top')
        player = random.choice(players[:top_n] if top_n else players)
        card = await HttpClient.get_buffer(player.card_url)
        return [Reply.to(data).image_buffer(card, f'*{player.name}* — ⭐ {player.overall}')]

    def _pool_size(self, top_n: int, league: LeagueInfo | None) -> int:
        if top_n > 0:
            return top_n
        return self.LEAGUE_POOL if league else self.GLOBAL_POOL

    @classmethod
    def _build_caption(cls, player: TmPlayer, league: LeagueInfo | None, season: str) -> str:
        club_flag = league.flag if league else ''
        position = POSITION_LABELS.get(player.position, player.position)
        nationality = nationality_pt(player.nationality)
        lines: list[str] = [
            f'*{player.name}* — {position}',
            '',
            f'🎂 {player.age} anos   {player.nationality_flag_emoji} {nationality}',
        ]
        lines.extend(cls._birth_line(player.profile))
        lines.append(f'🏟️ {player.club} {club_flag}')
        lines.extend(cls._physical_line(player.profile))
        lines.extend(
            ['', f'💰 {format_euros(player.market_value)}', SEASON_FOOTER.format(season=season)]
        )
        return '\n'.join(lines)

    @staticmethod
    def _birth_line(profile: PlayerProfile) -> list[str]:
        city, country = profile.birth_city, profile.birth_country
        if not city and not country:
            return []
        country_name = nationality_pt(country)
        parts = [country_name] if city == country else [city, country_name]
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
