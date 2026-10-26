"""Group players by role and assign them to formation slots."""

import random

from bot.data.football_formations import Formation
from bot.data.transfermarkt_positions import POSITION_ROLES
from bot.domain.models.football import TmPlayer
from bot.domain.services.lineup_assigner import LineupAssigner


class LineupBuilder:
    @staticmethod
    def from_players(
        players: list[TmPlayer], formation: Formation, per_role: int | None = None
    ) -> list[TmPlayer | None]:
        role_pools: dict[str, list[TmPlayer]] = {}
        for player in players:
            role = POSITION_ROLES.get(player.position)
            if role:
                role_pools.setdefault(role, []).append(player)
        for role, pool in role_pools.items():
            role_pools[role] = pool[:per_role]
            random.shuffle(role_pools[role])

        return LineupAssigner.assign_slots(role_pools, formation)
