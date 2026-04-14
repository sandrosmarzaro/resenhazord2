"""Transfermarkt competition code → display priority.

Lower value = higher priority (shown first, always included in capped
sections). Ordering reflects user intent for `,placar`: Brazilian top flight
first, then Top-5 Europe, then a second tier of national leagues, then
continental club competitions, then Opta-ranked long tail.

Opta reference:
https://theanalyst.com/articles/strongest-football-leagues-in-the-world-opta-power-rankings
"""

DEFAULT_PRIORITY: int = 99

LEAGUE_PRIORITY: dict[str, int] = {
    'BRA1': 0,
    'GB1': 1,
    'ES1': 1,
    'IT1': 1,
    'L1': 1,
    'FR1': 1,
    'AR1N': 2,
    'ARG1': 2,
    'BE1': 2,
    'PO1': 2,
    'NL1': 2,
    'TR1': 2,
    'MEX1': 3,
    'MLS1': 3,
    'SC1': 3,
    'RU1': 3,
    'A1': 3,
    'GR1': 3,
    'C1': 3,
    'UKR1': 3,
    'SA1': 3,
    'CL': 4,
    'EL': 4,
    'UCOL': 4,
    'CLI': 4,
    'CS': 4,
    'CCL': 4,
    'BRA2': 5,
    'BRA3': 5,
    'BRNE': 5,
    'ARG2': 5,
    'ES2': 5,
    'GB2': 5,
    'IT2': 5,
    'L2': 5,
    'FR2': 5,
    'NL2': 5,
    'PO2': 5,
}


def league_priority(competition_code: str) -> int:
    return LEAGUE_PRIORITY.get(competition_code, DEFAULT_PRIORITY)
