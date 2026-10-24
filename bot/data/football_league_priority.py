"""ESPN league slug → display priority for `,placar`.

Lower value = higher priority (shown first, always included in capped
sections): Brazilian top flight first, then the big continental cups and
Top-5 Europe, then a second tier of leagues and cups.
"""

DEFAULT_PRIORITY: int = 99

LEAGUE_PRIORITY: dict[str, int] = {
    'bra.1': 0,
    'bra.copa_do_brazil': 1,
    'conmebol.libertadores': 1,
    'uefa.champions': 1,
    'eng.1': 1,
    'esp.1': 1,
    'ita.1': 1,
    'ger.1': 1,
    'fra.1': 1,
    'conmebol.sudamericana': 2,
    'uefa.europa': 2,
    'arg.1': 2,
    'por.1': 2,
    'ned.1': 2,
    'usa.1': 3,
    'mex.1': 3,
    'bra.2': 5,
}


def league_priority(competition_code: str) -> int:
    return LEAGUE_PRIORITY.get(competition_code, DEFAULT_PRIORITY)
