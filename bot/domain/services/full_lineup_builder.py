"""Build full team lineup with field image."""

import asyncio
from typing import ClassVar

from bot.data.football import LEAGUES
from bot.data.football_formations import Formation
from bot.domain.models.football import TmPlayer
from bot.domain.services.football_field.build_field import build_football_field
from bot.domain.services.lineup_builder import LineupBuilder
from bot.domain.services.market_dataset import MarketDataset
from bot.domain.services.player_assets import PlayerAssets
from bot.domain.services.transfermarkt.service import TransfermarktService


class FullLineupBuilder:
    GLOBAL_ROLE_POOL: ClassVar[int] = 100

    @classmethod
    async def build(
        cls,
        league_code: str | None,
        formation: Formation,
        top_n: int,
    ) -> tuple[bytes, str]:
        ordered = await cls._lineup(league_code, formation, top_n)
        photos_ordered, badge_images = await PlayerAssets.fetch(ordered)

        names = [p.name if p else '' for p in ordered]
        flag_emojis = [
            (p.nationality_flag_emoji if p and p.nationality_flag_emoji else None) for p in ordered
        ]
        overlays = list(zip(flag_emojis, badge_images, strict=False))
        total_value = TransfermarktService.sum_market_values(ordered)
        field_image = await asyncio.to_thread(
            build_football_field, photos_ordered, names, formation, overlays, total_value
        )

        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        if total_value:
            caption += f'\n💰 {total_value}'
        return field_image, caption

    @classmethod
    async def _lineup(
        cls, league_code: str | None, formation: Formation, top_n: int
    ) -> list[TmPlayer | None]:
        league = LEAGUES.get(league_code) if league_code else None
        players = await MarketDataset.players(league.tm_id if league else '')
        # A league XI draws from whole squads; the world XI from the top of each role.
        per_role = None if league else (top_n if top_n > 0 else cls.GLOBAL_ROLE_POOL)
        return LineupBuilder.from_players(players, formation, per_role)
