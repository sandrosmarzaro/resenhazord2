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
    # ── 4-back, 3-mid (flat) ─────────────────────────────────────────────────
    Formation(
        name='4-3-3',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.15, 0.70),
            Slot('DEF', 0.38, 0.70),
            Slot('DEF', 0.62, 0.70),
            Slot('DEF', 0.85, 0.70),
            Slot('MID', 0.20, 0.50),
            Slot('MID', 0.50, 0.50),
            Slot('MID', 0.80, 0.50),
            Slot('ATT', 0.15, 0.18),
            Slot('ATT', 0.50, 0.13),
            Slot('ATT', 0.85, 0.18),
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
            Slot('MID', 0.12, 0.50),
            Slot('MID', 0.37, 0.50),
            Slot('MID', 0.63, 0.50),
            Slot('MID', 0.88, 0.50),
            Slot('ATT', 0.35, 0.14),
            Slot('ATT', 0.65, 0.14),
        ],
    ),
    # ── 4-back, layered mid ───────────────────────────────────────────────────
    Formation(
        name='4-2-3-1',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.35, 0.57),
            Slot('MID', 0.65, 0.57),
            Slot('MID', 0.15, 0.40),
            Slot('MID', 0.50, 0.40),
            Slot('MID', 0.85, 0.40),
            Slot('ATT', 0.50, 0.13),
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
            Slot('MID', 0.50, 0.59),
            Slot('MID', 0.12, 0.46),
            Slot('MID', 0.37, 0.46),
            Slot('MID', 0.63, 0.46),
            Slot('MID', 0.88, 0.46),
            Slot('ATT', 0.50, 0.13),
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
            Slot('MID', 0.50, 0.60),
            Slot('MID', 0.28, 0.49),
            Slot('MID', 0.72, 0.49),
            Slot('MID', 0.50, 0.38),
            Slot('ATT', 0.35, 0.14),
            Slot('ATT', 0.65, 0.14),
        ],
    ),
    # ── 4-back, mid triangles ─────────────────────────────────────────────────
    Formation(
        name='4-3-3 (Tri. Atq.)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.15, 0.70),
            Slot('DEF', 0.38, 0.70),
            Slot('DEF', 0.62, 0.70),
            Slot('DEF', 0.85, 0.70),
            Slot('MID', 0.50, 0.57),  # 1 DM (base of triangle)
            Slot('MID', 0.26, 0.44),  # 2 wide (top of triangle)
            Slot('MID', 0.74, 0.44),
            Slot('ATT', 0.15, 0.18),
            Slot('ATT', 0.50, 0.13),
            Slot('ATT', 0.85, 0.18),
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
            Slot('MID', 0.30, 0.55),  # 2 DM (base of triangle)
            Slot('MID', 0.70, 0.55),
            Slot('MID', 0.50, 0.42),  # 1 CAM (tip)
            Slot('ATT', 0.15, 0.18),
            Slot('ATT', 0.50, 0.13),
            Slot('ATT', 0.85, 0.18),
        ],
    ),
    # ── 4-back, diamond mid ───────────────────────────────────────────────────
    Formation(
        name='4-4-2 (Diamante)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.50, 0.59),  # DM (bottom of diamond)
            Slot('MID', 0.25, 0.48),  # left
            Slot('MID', 0.75, 0.48),  # right
            Slot('MID', 0.50, 0.38),  # CAM (top of diamond)
            Slot('ATT', 0.35, 0.14),
            Slot('ATT', 0.65, 0.14),
        ],
    ),
    # ── 4-back, christmas tree / layered ─────────────────────────────────────
    Formation(
        name='4-3-2-1 (Árvore)',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.20, 0.57),  # 3 flat DM
            Slot('MID', 0.50, 0.57),
            Slot('MID', 0.80, 0.57),
            Slot('MID', 0.35, 0.40),  # 2 AM (narrower)
            Slot('MID', 0.65, 0.40),
            Slot('ATT', 0.50, 0.13),
        ],
    ),
    # ── 4-back, 5-mid ────────────────────────────────────────────────────────
    Formation(
        name='4-5-1',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.10, 0.50),
            Slot('MID', 0.30, 0.50),
            Slot('MID', 0.50, 0.50),
            Slot('MID', 0.70, 0.50),
            Slot('MID', 0.90, 0.50),
            Slot('ATT', 0.50, 0.14),
        ],
    ),
    # ── 3-back formations ─────────────────────────────────────────────────────
    Formation(
        name='3-5-2',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.20, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.80, 0.70),
            Slot('MID', 0.10, 0.50),
            Slot('MID', 0.30, 0.50),
            Slot('MID', 0.50, 0.50),
            Slot('MID', 0.70, 0.50),
            Slot('MID', 0.90, 0.50),
            Slot('ATT', 0.35, 0.14),
            Slot('ATT', 0.65, 0.14),
        ],
    ),
    Formation(
        name='3-4-3',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.20, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.80, 0.70),
            Slot('MID', 0.15, 0.50),
            Slot('MID', 0.40, 0.50),
            Slot('MID', 0.60, 0.50),
            Slot('MID', 0.85, 0.50),
            Slot('ATT', 0.15, 0.18),
            Slot('ATT', 0.50, 0.13),
            Slot('ATT', 0.85, 0.18),
        ],
    ),
    Formation(
        name='3-4-2-1',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.20, 0.72),
            Slot('DEF', 0.50, 0.72),
            Slot('DEF', 0.80, 0.72),
            Slot('MID', 0.12, 0.55),
            Slot('MID', 0.38, 0.55),
            Slot('MID', 0.62, 0.55),
            Slot('MID', 0.88, 0.55),
            Slot('MID', 0.35, 0.38),  # 2 CAM
            Slot('MID', 0.65, 0.38),
            Slot('ATT', 0.50, 0.13),
        ],
    ),
    # ── 5-back formations ─────────────────────────────────────────────────────
    Formation(
        name='5-3-2',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.10, 0.70),
            Slot('DEF', 0.30, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.70, 0.70),
            Slot('DEF', 0.90, 0.70),
            Slot('MID', 0.22, 0.50),
            Slot('MID', 0.50, 0.50),
            Slot('MID', 0.78, 0.50),
            Slot('ATT', 0.35, 0.14),
            Slot('ATT', 0.65, 0.14),
        ],
    ),
    Formation(
        name='5-2-3',
        slots=[
            Slot('GK', 0.50, 0.90),
            Slot('DEF', 0.10, 0.70),
            Slot('DEF', 0.30, 0.70),
            Slot('DEF', 0.50, 0.70),
            Slot('DEF', 0.70, 0.70),
            Slot('DEF', 0.90, 0.70),
            Slot('MID', 0.35, 0.50),
            Slot('MID', 0.65, 0.50),
            Slot('ATT', 0.15, 0.18),
            Slot('ATT', 0.50, 0.13),
            Slot('ATT', 0.85, 0.18),
        ],
    ),
]


def random_formation() -> Formation:
    return random.choice(FORMATIONS)  # noqa: S311
