"""Assign players to formation slots by role, scarcest-first with group fallback."""

from bot.data.football_formations import (
    ROLE_GROUPS,
    SCARCITY_ORDER,
    Formation,
    specific_roles,
)
from bot.domain.models.football import TmPlayer


class LineupAssigner:
    _DEFAULT_SCARCITY = 3

    @classmethod
    def assign_slots(
        cls,
        role_pools: dict[str, list[TmPlayer]],
        formation: Formation,
    ) -> list[TmPlayer | None]:
        slot_specific = specific_roles(formation)
        ordered: list[TmPlayer | None] = [None] * len(formation.slots)
        used: set[str] = set()

        slot_order = sorted(
            range(len(formation.slots)),
            key=lambda i: SCARCITY_ORDER.get(slot_specific[i], cls._DEFAULT_SCARCITY),
        )

        for i in slot_order:
            slot_role = formation.slots[i].role
            player = cls._find_player(slot_specific[i], role_pools, used, role=slot_role)
            if player:
                used.add(player.name)
            ordered[i] = player

        return ordered

    @classmethod
    def _find_player(
        cls,
        specific: str,
        role_pools: dict[str, list[TmPlayer]],
        used: set[str],
        *,
        role: str | None = None,
    ) -> TmPlayer | None:
        pool = role_pools.get(specific, [])
        player = next((p for p in pool if p.name not in used), None)
        if player:
            return player

        group = ROLE_GROUPS.get(specific, role)
        for other_role, other_pool in role_pools.items():
            if ROLE_GROUPS.get(other_role) != group:
                continue
            player = next((p for p in other_pool if p.name not in used), None)
            if player:
                return player

        return None
