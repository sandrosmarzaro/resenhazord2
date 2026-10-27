"""transfermarkt-datasets dump: a weekly public scrape of Transfermarkt on Cloudflare R2."""

from datetime import timedelta

MARKET_DATASET_URL = 'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/{table}.csv.gz'
MARKET_DATASET_TTL = timedelta(days=7)
# European seasons start in July; a dump without the current one has stopped updating.
SEASON_START_MONTH = 7
CLUB_BADGE_URL = 'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png'
# The dump is third-party data and the bot downloads these images, so only this host passes.
PLAYER_PHOTO_PREFIX = 'https://img.a.transfermarkt.technology/'
EUROS_PER_MILLION = 1_000_000
EUROS_PER_THOUSAND = 1_000
SEASON_FOOTER = '📅 Valores da temporada {season}'
