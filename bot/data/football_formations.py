"""Football formation definitions with player position coordinates."""

import random
from dataclasses import dataclass

# x: 0.0 = left edge, 1.0 = right edge
# y: 0.0 = top of canvas (attack end / enemy goal), 1.0 = bottom (goalkeeper end)
# Penalty area: y 0.0-0.18 (attack) and y 0.82-1.0 (defense)


@dataclass(frozen=True)
class Slot:
    role: str  # 'GK', 'DEF', 'MID', 'ATT'
    x: float
    y: float


@dataclass(frozen=True)
class Formation:
    name: str
    slots: list[Slot]


FORMATIONS: list[Formation] = [
    # -- 4-back, 3-mid (flat) -------------------------------------------------------
    Formation(
        name='4-3-3',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.15, 0.70),
            Slot('DEF', 0.38, 0.70),
            Slot('DEF', 0.62, 0.70),
            Slot('DEF', 0.85, 0.70),
            Slot('MID', 0.20, 0.44),
            Slot('MID', 0.50, 0.44),
            Slot('MID', 0.80, 0.44),
            Slot('ATT', 0.15, 0.19),
            Slot('ATT', 0.50, 0.14),
            Slot('ATT', 0.85, 0.19),
        ],
    ),
    Formation(
        name='4-4-2',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.70),
            Slot('DEF', 0.37, 0.70),
            Slot('DEF', 0.63, 0.70),
            Slot('DEF', 0.88, 0.70),
            Slot('MID', 0.12, 0.44),
            Slot('MID', 0.37, 0.44),
            Slot('MID', 0.63, 0.44),
            Slot('MID', 0.88, 0.44),
            Slot('ATT', 0.35, 0.15),
            Slot('ATT', 0.65, 0.15),
        ],
    ),
    # -- 4-back, layered mid --------------------------------------------------------
    Formation(
        name='4-2-3-1',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.35, 0.51),
            Slot('MID', 0.65, 0.51),
            Slot('MID', 0.15, 0.34),
            Slot('MID', 0.50, 0.34),
            Slot('MID', 0.85, 0.34),
            Slot('ATT', 0.50, 0.14),
        ],
    ),
    Formation(
        name='4-1-4-1',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.50, 0.53),
            Slot('MID', 0.12, 0.40),
            Slot('MID', 0.37, 0.40),
            Slot('MID', 0.63, 0.40),
            Slot('MID', 0.88, 0.40),
            Slot('ATT', 0.50, 0.14),
        ],
    ),
    Formation(
        name='4-1-2-1-2',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.50, 0.54),
            Slot('MID', 0.28, 0.43),
            Slot('MID', 0.72, 0.43),
            Slot('MID', 0.50, 0.32),
            Slot('ATT', 0.35, 0.15),
            Slot('ATT', 0.65, 0.15),
        ],
    ),
    # -- 4-back, mid triangles ------------------------------------------------------
    Formation(
        name='4-3-3 (Tri. Atq.)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.15, 0.70),
            Slot('DEF', 0.38, 0.70),
            Slot('DEF', 0.62, 0.70),
            Slot('DEF', 0.85, 0.70),
            Slot('MID', 0.50, 0.51),  # 1 DM (base of triangle)
            Slot('MID', 0.26, 0.38),  # 2 wide (top of triangle)
            Slot('MID', 0.74, 0.38),
            Slot('ATT', 0.15, 0.19),
            Slot('ATT', 0.50, 0.14),
            Slot('ATT', 0.85, 0.19),
        ],
    ),
    Formation(
        name='4-3-3 (Tri. Def.)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.15, 0.70),
            Slot('DEF', 0.38, 0.70),
            Slot('DEF', 0.62, 0.70),
            Slot('DEF', 0.85, 0.70),
            Slot('MID', 0.30, 0.49),  # 2 DM (base of triangle)
            Slot('MID', 0.70, 0.49),
            Slot('MID', 0.50, 0.36),  # 1 CAM (tip)
            Slot('ATT', 0.15, 0.19),
            Slot('ATT', 0.50, 0.14),
            Slot('ATT', 0.85, 0.19),
        ],
    ),
    # -- 4-back, diamond mid --------------------------------------------------------
    Formation(
        name='4-4-2 (Diamante)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.50, 0.53),  # DM (bottom of diamond)
            Slot('MID', 0.25, 0.42),  # left
            Slot('MID', 0.75, 0.42),  # right
            Slot('MID', 0.50, 0.32),  # CAM (top of diamond)
            Slot('ATT', 0.35, 0.15),
            Slot('ATT', 0.65, 0.15),
        ],
    ),
    # -- 4-back, christmas tree / layered -------------------------------------------
    Formation(
        name='4-3-2-1 (Árvore)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.20, 0.51),  # 3 flat DM
            Slot('MID', 0.50, 0.51),
            Slot('MID', 0.80, 0.51),
            Slot('MID', 0.35, 0.34),  # 2 AM (narrower)
            Slot('MID', 0.65, 0.34),
            Slot('ATT', 0.50, 0.14),
        ],
    ),
    # -- 4-back, 5-mid (2-3 layered) ------------------------------------------------
    Formation(
        name='4-5-1',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.30, 0.56),  # 2 DM
            Slot('MID', 0.70, 0.56),
            Slot('MID', 0.12, 0.39),  # 3 AM
            Slot('MID', 0.50, 0.39),
            Slot('MID', 0.88, 0.39),
            Slot('ATT', 0.50, 0.15),
        ],
    ),
    # -- 3-back formations ----------------------------------------------------------
    Formation(
        name='3-5-2',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.20, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.80, 0.70),
            Slot('MID', 0.28, 0.56),  # 2 DM (pentagon base)
            Slot('MID', 0.72, 0.56),
            Slot('MID', 0.50, 0.44),  # 1 CM (center)
            Slot('MID', 0.12, 0.33),  # 2 WM (wings)
            Slot('MID', 0.88, 0.33),
            Slot('ATT', 0.35, 0.15),
            Slot('ATT', 0.65, 0.15),
        ],
    ),
    Formation(
        name='3-4-3',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.20, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.80, 0.70),
            Slot('MID', 0.10, 0.44),
            Slot('MID', 0.35, 0.44),
            Slot('MID', 0.65, 0.44),
            Slot('MID', 0.90, 0.44),
            Slot('ATT', 0.15, 0.19),
            Slot('ATT', 0.50, 0.14),
            Slot('ATT', 0.85, 0.19),
        ],
    ),
    Formation(
        name='3-4-2-1',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.20, 0.72),
            Slot('DEF', 0.50, 0.72),
            Slot('DEF', 0.80, 0.72),
            Slot('MID', 0.12, 0.49),
            Slot('MID', 0.38, 0.49),
            Slot('MID', 0.62, 0.49),
            Slot('MID', 0.88, 0.49),
            Slot('MID', 0.35, 0.32),  # 2 CAM
            Slot('MID', 0.65, 0.32),
            Slot('ATT', 0.50, 0.14),
        ],
    ),
    # -- 5-back formations (diamond mid) -------------------------------------------
    Formation(
        name='5-4-1 (Losango)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.10, 0.70),
            Slot('DEF', 0.30, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.70, 0.70),
            Slot('DEF', 0.90, 0.70),
            Slot('MID', 0.50, 0.53),  # DM (base)
            Slot('MID', 0.22, 0.41),  # left
            Slot('MID', 0.78, 0.41),  # right
            Slot('MID', 0.50, 0.30),  # CAM (tip)
            Slot('ATT', 0.50, 0.15),
        ],
    ),
    Formation(
        name='5-3-2 (Triângulo)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.10, 0.70),
            Slot('DEF', 0.30, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.70, 0.70),
            Slot('DEF', 0.90, 0.70),
            Slot('MID', 0.28, 0.50),  # 2 DM (base of triangle)
            Slot('MID', 0.72, 0.50),
            Slot('MID', 0.50, 0.33),  # CAM (tip)
            Slot('ATT', 0.35, 0.15),
            Slot('ATT', 0.65, 0.15),
        ],
    ),
]


_DM_Y_THRESHOLD = 0.50
_AM_Y_THRESHOLD = 0.36

ROLE_GROUPS: dict[str, str] = {
    'GK': 'GK',
    'CB': 'DEF',
    'LB': 'DEF',
    'RB': 'DEF',
    'DM': 'MID',
    'CM': 'MID',
    'AM': 'MID',
    'LW': 'ATT',
    'ST': 'ATT',
    'RW': 'ATT',
}


_MIN_DEF_FOR_FULLBACK = 3


def _label_def(slots: list[Slot], indexes: list[int], result: list[str]) -> None:
    sorted_idx = sorted(indexes, key=lambda i: slots[i].x)
    last = len(sorted_idx) - 1
    for rank, i in enumerate(sorted_idx):
        if len(sorted_idx) >= _MIN_DEF_FOR_FULLBACK and rank == 0:
            result[i] = 'LB'
        elif len(sorted_idx) >= _MIN_DEF_FOR_FULLBACK and rank == last:
            result[i] = 'RB'
        else:
            result[i] = 'CB'


def _label_att(slots: list[Slot], indexes: list[int], result: list[str]) -> None:
    sorted_idx = sorted(indexes, key=lambda i: slots[i].x)
    if len(sorted_idx) <= 2:  # noqa: PLR2004
        for i in sorted_idx:
            result[i] = 'ST'
        return
    result[sorted_idx[0]] = 'LW'
    result[sorted_idx[-1]] = 'RW'
    for i in sorted_idx[1:-1]:
        result[i] = 'ST'


def _label_mid(slots: list[Slot], indexes: list[int], result: list[str]) -> None:
    for i in indexes:
        y = slots[i].y
        if y >= _DM_Y_THRESHOLD:
            result[i] = 'DM'
        elif y < _AM_Y_THRESHOLD:
            result[i] = 'AM'
        else:
            result[i] = 'CM'


_LABELERS = {'DEF': _label_def, 'MID': _label_mid, 'ATT': _label_att}


def specific_roles(formation: Formation) -> list[str]:
    """Derive a CB/LB/RB/DM/CM/AM/LW/ST/RW label for each slot from its (x, y)."""
    by_role: dict[str, list[int]] = {}
    for i, slot in enumerate(formation.slots):
        by_role.setdefault(slot.role, []).append(i)

    result: list[str] = [''] * len(formation.slots)
    for role, indexes in by_role.items():
        if role == 'GK':
            for i in indexes:
                result[i] = 'GK'
            continue
        labeler = _LABELERS.get(role)
        if labeler:
            labeler(formation.slots, indexes, result)
    return result


SCARCITY_ORDER: dict[str, int] = {
    'LB': 0,
    'RB': 0,
    'LW': 0,
    'RW': 0,
    'AM': 1,
    'DM': 1,
    'GK': 2,
}


def random_formation() -> Formation:
    return random.choice(FORMATIONS)  # noqa: S311
