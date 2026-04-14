"""Transfermarkt URL templates, HTTP headers, and pagination constants."""

GLOBAL_URL = 'https://www.transfermarkt.com.br/spieler-statistik/wertvollstespieler/marktwertetop'
LIVE_URL = 'https://www.transfermarkt.com.br/live/'
POSITION_FILTER_URL = (
    'https://www.transfermarkt.com.br/spieler-statistik/wertvollstespieler/'
    'marktwertetop/plus/0/galerie/0'
)
CLUBS_URL = (
    'https://www.transfermarkt.com.br/spieler-statistik/wertvollstemannschaften/marktwertetop'
)
LEAGUE_URL = 'https://www.transfermarkt.com.br/{slug}/marktwerte/wettbewerb/{tm_id}/page/{page}'
SQUAD_VALUES_URL = 'https://www.transfermarkt.com.br/{slug}/startseite/wettbewerb/{tm_id}'
CLUB_SQUAD_URL = (
    'https://www.transfermarkt.com.br/club/kader/verein/{club_id}/saison_id/{season}/plus/1'
)

DEFAULT_SEASON = '2025'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://www.transfermarkt.com.br/',
}

PLAYERS_PER_PAGE = 25
GLOBAL_MAX_PAGES = 40
LEAGUE_MAX_PAGES = 4
POSITION_MAX_PAGES = 4
