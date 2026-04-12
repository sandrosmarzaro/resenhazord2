"""Build lineup role pools from Transfermarkt data and assign to formation slots."""

import asyncio
import random

from bot.data.football_formations import Formation, specific_roles
from bot.data.transfermarkt_positions import POSITION_ROLES
from bot.domain.models.football import TmPlayer
from bot.domain.services.lineup_assigner import LineupAssigner
from bot.domain.services.transfermarkt.service import TransfermarktService


class LineupBuilder:
    @staticmethod
    async def from_position_queries(
        formation: Formation, max_pages: int, top_n: int | None = None
    ) -> list[TmPlayer | None]:
        slot_specific = specific_roles(formation)
        distinct_roles = sorted(set(slot_specific))

        results = await asyncio.gather(
            *[
                TransfermarktService.fetch_by_specific_position(role, max_pages)
                for role in distinct_roles
            ]
        )
        role_pools: dict[str, list[TmPlayer]] = {}
        for role, players in zip(distinct_roles, results, strict=True):
            pool = list(players[:top_n]) if top_n else list(players)
            random.shuffle(pool)
            role_pools[role] = pool

        return LineupAssigner.assign_slots(role_pools, formation)

    @staticmethod
    def from_league_squad(players: list[TmPlayer], formation: Formation) -> list[TmPlayer | None]:
        specific_pools: dict[str, list[TmPlayer]] = {}
        for p in players:
            role = POSITION_ROLES.get(p.position)
            if role:
                specific_pools.setdefault(role, []).append(p)
        for pool in specific_pools.values():
            random.shuffle(pool)

        return LineupAssigner.assign_slots(specific_pools, formation)
