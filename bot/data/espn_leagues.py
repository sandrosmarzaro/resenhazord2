"""Leagues polled for ,placar, in display-priority order (see football_league_priority)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreboardLeague:
    slug: str
    name: str
    flag: str


SCOREBOARD_LEAGUES: tuple[ScoreboardLeague, ...] = (
    ScoreboardLeague('bra.1', 'Brasileirão', '🇧🇷'),
    ScoreboardLeague('bra.copa_do_brazil', 'Copa do Brasil', '🇧🇷'),
    ScoreboardLeague('conmebol.libertadores', 'Libertadores', '🌎'),
    ScoreboardLeague('uefa.champions', 'Champions League', '🇪🇺'),
    ScoreboardLeague('eng.1', 'Premier League', '🏴󠁧󠁢󠁥󠁮󠁧󠁿'),
    ScoreboardLeague('esp.1', 'La Liga', '🇪🇸'),
    ScoreboardLeague('ita.1', 'Serie A', '🇮🇹'),
    ScoreboardLeague('ger.1', 'Bundesliga', '🇩🇪'),
    ScoreboardLeague('fra.1', 'Ligue 1', '🇫🇷'),
    ScoreboardLeague('conmebol.sudamericana', 'Sul-Americana', '🌎'),
    ScoreboardLeague('uefa.europa', 'Europa League', '🇪🇺'),
    ScoreboardLeague('arg.1', 'Liga Profesional', '🇦🇷'),
    ScoreboardLeague('por.1', 'Primeira Liga', '🇵🇹'),
    ScoreboardLeague('ned.1', 'Eredivisie', '🇳🇱'),
    ScoreboardLeague('usa.1', 'MLS', '🇺🇸'),
    ScoreboardLeague('mex.1', 'Liga MX', '🇲🇽'),
    ScoreboardLeague('bra.2', 'Série B', '🇧🇷'),
)
