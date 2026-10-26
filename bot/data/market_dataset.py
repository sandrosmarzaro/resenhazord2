"""transfermarkt-datasets dump: a weekly public scrape of Transfermarkt on Cloudflare R2."""

from datetime import timedelta

MARKET_DATASET_URL = 'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/{table}.csv.gz'
MARKET_DATASET_TTL = timedelta(days=7)
MARKET_DATASET_STALE_AFTER = timedelta(days=30)
CLUB_BADGE_URL = 'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png'
# The dump is third-party data and the bot downloads these images, so only this host passes.
PLAYER_PHOTO_PREFIX = 'https://img.a.transfermarkt.technology/'
