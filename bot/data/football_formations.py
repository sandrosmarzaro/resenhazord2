"""Football formation definitions with player position coordinates."""

import random
from dataclasses import dataclass

# x: 0.0 = left edge, 1.0 = right edge
# y: 0.0 = top of canvas (attack), 1.0 = bottom of canvas (goalkeeper end)


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
    Formation(
        name='4-3-3',
        slots=[
            Slot('GK', 0.50, 0.92),
            Slot('DEF', 0.15, 0.72),
            Slot('DEF', 0.38, 0.72),
            Slot('DEF', 0.62, 0.72),
            Slot('DEF', 0.85, 0.72),
            Slot('MID', 0.20, 0.50),
            Slot('MID', 0.50, 0.50),
            Slot('MID', 0.80, 0.50),
            Slot('ATT', 0.15, 0.22),
            Slot('ATT', 0.50, 0.18),
            Slot('ATT', 0.85, 0.22),
        ],
    ),
    Formation(
        name='4-4-2',
        slots=[
            Slot('GK', 0.50, 0.92),
            Slot('DEF', 0.12, 0.72),
            Slot('DEF', 0.37, 0.72),
            Slot('DEF', 0.63, 0.72),
            Slot('DEF', 0.88, 0.72),
            Slot('MID', 0.12, 0.50),
            Slot('MID', 0.37, 0.50),
            Slot('MID', 0.63, 0.50),
            Slot('MID', 0.88, 0.50),
            Slot('ATT', 0.35, 0.22),
            Slot('ATT', 0.65, 0.22),
        ],
    ),
    Formation(
        name='4-2-3-1',
        slots=[
            Slot('GK', 0.50, 0.92),
            Slot('DEF', 0.12, 0.74),
            Slot('DEF', 0.37, 0.74),
            Slot('DEF', 0.63, 0.74),
            Slot('DEF', 0.88, 0.74),
            Slot('MID', 0.35, 0.58),
            Slot('MID', 0.65, 0.58),
            Slot('MID', 0.15, 0.38),
            Slot('MID', 0.50, 0.38),
            Slot('MID', 0.85, 0.38),
            Slot('ATT', 0.50, 0.18),
        ],
    ),
    Formation(
        name='3-5-2',
        slots=[
            Slot('GK', 0.50, 0.92),
            Slot('DEF', 0.20, 0.72),
            Slot('DEF', 0.50, 0.72),
            Slot('DEF', 0.80, 0.72),
            Slot('MID', 0.10, 0.52),
            Slot('MID', 0.30, 0.52),
            Slot('MID', 0.50, 0.52),
            Slot('MID', 0.70, 0.52),
            Slot('MID', 0.90, 0.52),
            Slot('ATT', 0.35, 0.22),
            Slot('ATT', 0.65, 0.22),
        ],
    ),
    Formation(
        name='3-4-3',
        slots=[
            Slot('GK', 0.50, 0.92),
            Slot('DEF', 0.20, 0.72),
            Slot('DEF', 0.50, 0.72),
            Slot('DEF', 0.80, 0.72),
            Slot('MID', 0.15, 0.52),
            Slot('MID', 0.40, 0.52),
            Slot('MID', 0.60, 0.52),
            Slot('MID', 0.85, 0.52),
            Slot('ATT', 0.15, 0.22),
            Slot('ATT', 0.50, 0.18),
            Slot('ATT', 0.85, 0.22),
        ],
    ),
    Formation(
        name='5-3-2',
        slots=[
            Slot('GK', 0.50, 0.92),
            Slot('DEF', 0.10, 0.72),
            Slot('DEF', 0.30, 0.72),
            Slot('DEF', 0.50, 0.72),
            Slot('DEF', 0.70, 0.72),
            Slot('DEF', 0.90, 0.72),
            Slot('MID', 0.22, 0.50),
            Slot('MID', 0.50, 0.50),
            Slot('MID', 0.78, 0.50),
            Slot('ATT', 0.35, 0.22),
            Slot('ATT', 0.65, 0.22),
        ],
    ),
    Formation(
        name='4-1-4-1',
        slots=[
            Slot('GK', 0.50, 0.92),
            Slot('DEF', 0.12, 0.74),
            Slot('DEF', 0.37, 0.74),
            Slot('DEF', 0.63, 0.74),
            Slot('DEF', 0.88, 0.74),
            Slot('MID', 0.50, 0.62),
            Slot('MID', 0.12, 0.48),
            Slot('MID', 0.37, 0.48),
            Slot('MID', 0.63, 0.48),
            Slot('MID', 0.88, 0.48),
            Slot('ATT', 0.50, 0.18),
        ],
    ),
]


def random_formation() -> Formation:
    return random.choice(FORMATIONS)  # noqa: S311
