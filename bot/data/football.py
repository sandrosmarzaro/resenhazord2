"""Static league metadata for football commands."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LeagueInfo:
    code: str
    name: str
    country: str
    flag: str
    tm_id: str
    tm_slug: str
    sportsdb_id: int
    sportsdb_name: str
    sportsdb_season: str


LEAGUES: dict[str, LeagueInfo] = {
    'pl': LeagueInfo(
        code='pl',
        name='Premier League',
        country='England',
        flag='🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        tm_id='GB1',
        tm_slug='premier-league',
        sportsdb_id=4328,
        sportsdb_name='English Premier League',
        sportsdb_season='2024-2025',
    ),
    'la': LeagueInfo(
        code='la',
        name='La Liga',
        country='Spain',
        flag='🇪🇸',
        tm_id='ES1',
        tm_slug='laliga',
        sportsdb_id=4335,
        sportsdb_name='Spanish La Liga',
        sportsdb_season='2024-2025',
    ),
    'bl': LeagueInfo(
        code='bl',
        name='Bundesliga',
        country='Germany',
        flag='🇩🇪',
        tm_id='L1',
        tm_slug='bundesliga',
        sportsdb_id=4331,
        sportsdb_name='German Bundesliga',
        sportsdb_season='2024-2025',
    ),
    'sa': LeagueInfo(
        code='sa',
        name='Serie A',
        country='Italy',
        flag='🇮🇹',
        tm_id='IT1',
        tm_slug='serie-a',
        sportsdb_id=4332,
        sportsdb_name='Italian Serie A',
        sportsdb_season='2024-2025',
    ),
    'l1': LeagueInfo(
        code='l1',
        name='Ligue 1',
        country='France',
        flag='🇫🇷',
        tm_id='FR1',
        tm_slug='ligue-1',
        sportsdb_id=4334,
        sportsdb_name='French Ligue 1',
        sportsdb_season='2024-2025',
    ),
    'br': LeagueInfo(
        code='br',
        name='Brasileirão',
        country='Brasil',
        flag='🇧🇷',
        tm_id='BRA1',
        tm_slug='campeonato-brasileiro-serie-a',
        sportsdb_id=4351,
        sportsdb_name='Brazilian Série A',
        sportsdb_season='2024',
    ),
    'ar': LeagueInfo(
        code='ar',
        name='Liga Profesional',
        country='Argentina',
        flag='🇦🇷',
        tm_id='AR1N',
        tm_slug='superliga',
        sportsdb_id=4406,
        sportsdb_name='Argentinian Primera Division',
        sportsdb_season='2024',
    ),
    'uy': LeagueInfo(
        code='uy',
        name='Primera División',
        country='Uruguai',
        flag='🇺🇾',
        tm_id='URU1',
        tm_slug='primera-division',
        sportsdb_id=4431,
        sportsdb_name='Uruguayan Primera Division',
        sportsdb_season='2024',
    ),
    'ec': LeagueInfo(
        code='ec',
        name='LigaPro',
        country='Equador',
        flag='🇪🇨',
        tm_id='EC1N',
        tm_slug='ligapro-serie-a',
        sportsdb_id=4779,
        sportsdb_name='Ecuadorian Serie A',
        sportsdb_season='2024',
    ),
    'co': LeagueInfo(
        code='co',
        name='Liga BetPlay',
        country='Colômbia',
        flag='🇨🇴',
        tm_id='COL1',
        tm_slug='primera-a',
        sportsdb_id=4441,
        sportsdb_name='Colombian Primera A',
        sportsdb_season='2024',
    ),
}

LEAGUE_CODES: list[str] = list(LEAGUES.keys())

LEAGUES_BY_TM_ID: dict[str, LeagueInfo] = {lg.tm_id: lg for lg in LEAGUES.values()}
