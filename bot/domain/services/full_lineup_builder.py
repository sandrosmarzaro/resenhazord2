"""Build full team lineup with field image."""

import asyncio
import random
from collections.abc import Sequence
from statistics import mean
from typing import ClassVar

from bot.data.football import LEAGUES
from bot.data.football_formations import Formation, specific_roles
from bot.data.market_dataset import SEASON_FOOTER
from bot.domain.models.football import LineupPlayer, TmPlayer
from bot.domain.services.fifa_ratings import FifaRatings
from bot.domain.services.football_field.build_field import build_football_field
from bot.domain.services.lineup_assigner import LineupAssigner
from bot.domain.services.lineup_builder import LineupBuilder
from bot.domain.services.market_dataset import MarketDataset, format_euros
from bot.domain.services.player_assets import PlayerAssets


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
        total = sum(player.market_value for player in ordered if player)
        total_value = format_euros(total) if total else None
        field_image = await cls._render(ordered, formation, total_value)

        caption = f'⚽ *Escalação Aleatória* — {formation.name}'
        if total_value:
            caption += f'\n💰 {total_value}'
        caption += f'\n{SEASON_FOOTER.format(season=await MarketDataset.season())}'
        return field_image, caption

    @classmethod
    async def build_fifa(cls, formation: Formation, top_n: int) -> tuple[bytes, str]:
        pools = await FifaRatings.role_pools(set(specific_roles(formation)))
        per_role = top_n if top_n > 0 else cls.GLOBAL_ROLE_POOL
        role_pools = {
            role: random.sample(pool[:per_role], len(pool[:per_role]))
            for role, pool in pools.items()
        }
        ordered = LineupAssigner.assign_slots(role_pools, formation)
        ratings = [player.overall for player in ordered if player]
        average = round(mean(ratings))
        # The field font has no emoji glyphs.
        field_image = await cls._render(ordered, formation, f'OVR médio {average}')
        return field_image, f'⚽ *Escalação FIFA* — {formation.name}\n⭐ Overall médio: {average}'

    @staticmethod
    async def _render(
        ordered: Sequence[LineupPlayer | None], formation: Formation, label: str | None
    ) -> bytes:
        photos, badges = await PlayerAssets.fetch(ordered)
        names = [player.name if player else '' for player in ordered]
        flags = [(player.nationality_flag_emoji or None) if player else None for player in ordered]
        overlays = list(zip(flags, badges, strict=False))
        return await asyncio.to_thread(
            build_football_field, photos, names, formation, overlays, label
        )

    @classmethod
    async def _lineup(
        cls, league_code: str | None, formation: Formation, top_n: int
    ) -> list[TmPlayer | None]:
        league = LEAGUES.get(league_code) if league_code else None
        players = await MarketDataset.players(league.tm_id if league else '')
        # A league XI draws from whole squads; the world XI from the top of each role.
        if league:
            return LineupBuilder.from_players(players, formation)
        per_role = top_n if top_n > 0 else cls.GLOBAL_ROLE_POOL
        return LineupBuilder.from_players(players, formation, per_role)
