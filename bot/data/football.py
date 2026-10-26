"""Static league metadata for football commands."""

from dataclasses import dataclass
from datetime import timedelta, timezone

BR_TIMEZONE = timezone(timedelta(hours=-3))


@dataclass(frozen=True)
class LeagueInfo:
    code: str
    name: str
    country: str
    flag: str
    tm_id: str
    tm_slug: str
    espn_slug: str


LEAGUES: dict[str, LeagueInfo] = {
    'pl': LeagueInfo(
        code='pl',
        name='Premier League',
        country='England',
        flag='🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        tm_id='GB1',
        tm_slug='premier-league',
        espn_slug='eng.1',
    ),
    'la': LeagueInfo(
        code='la',
        name='La Liga',
        country='Spain',
        flag='🇪🇸',
        tm_id='ES1',
        tm_slug='laliga',
        espn_slug='esp.1',
    ),
    'bl': LeagueInfo(
        code='bl',
        name='Bundesliga',
        country='Germany',
        flag='🇩🇪',
        tm_id='L1',
        tm_slug='bundesliga',
        espn_slug='ger.1',
    ),
    'sa': LeagueInfo(
        code='sa',
        name='Serie A',
        country='Italy',
        flag='🇮🇹',
        tm_id='IT1',
        tm_slug='serie-a',
        espn_slug='ita.1',
    ),
    'l1': LeagueInfo(
        code='l1',
        name='Ligue 1',
        country='France',
        flag='🇫🇷',
        tm_id='FR1',
        tm_slug='ligue-1',
        espn_slug='fra.1',
    ),
    'br': LeagueInfo(
        code='br',
        name='Brasileirão',
        country='Brasil',
        flag='🇧🇷',
        tm_id='BRA1',
        tm_slug='campeonato-brasileiro-serie-a',
        espn_slug='bra.1',
    ),
    'ar': LeagueInfo(
        code='ar',
        name='Liga Profesional',
        country='Argentina',
        flag='🇦🇷',
        tm_id='ARG1',
        tm_slug='superliga',
        espn_slug='arg.1',
    ),
    'uy': LeagueInfo(
        code='uy',
        name='Primera División',
        country='Uruguai',
        flag='🇺🇾',
        tm_id='URU1',
        tm_slug='primera-division',
        espn_slug='uru.1',
    ),
    'ec': LeagueInfo(
        code='ec',
        name='LigaPro',
        country='Equador',
        flag='🇪🇨',
        tm_id='EC1N',
        tm_slug='ligapro-serie-a',
        espn_slug='ecu.1',
    ),
    'co': LeagueInfo(
        code='co',
        name='Liga BetPlay',
        country='Colômbia',
        flag='🇨🇴',
        tm_id='COL1',
        tm_slug='primera-a',
        espn_slug='col.1',
    ),
}

LEAGUE_CODES: list[str] = list(LEAGUES.keys())
# Leagues covered by the transfermarkt-datasets dump (no Uruguay, Ecuador or Colombia).
MARKET_LEAGUE_CODES: list[str] = ['pl', 'la', 'bl', 'sa', 'l1', 'br', 'ar']

LEAGUES_BY_TM_ID: dict[str, LeagueInfo] = {lg.tm_id: lg for lg in LEAGUES.values()}
