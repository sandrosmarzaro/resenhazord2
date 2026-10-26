"""EA Sports FC ratings API: the public data behind ea.com/games/ea-sports-fc/ratings."""

from datetime import timedelta

FIFA_RATINGS_URL = 'https://drop-api.ea.com/rating/ea-sports-fc'
FIFA_PAGE_SIZE = 100
FIFA_MEN_GENDER = 0
FIFA_RATINGS_TTL = timedelta(days=7)

# EA position ids for each lineup role (football_formations.specific_roles).
FIFA_POSITION_IDS: dict[str, int] = {
    'GK': 0,
    'RB': 3,
    'CB': 5,
    'LB': 7,
    'DM': 10,
    'CM': 14,
    'AM': 18,
    'RW': 23,
    'ST': 25,
    'LW': 27,
}

# The bot downloads these images, so only EA's own hosts pass.
FIFA_IMAGE_PREFIXES: tuple[str, ...] = (
    'https://ratings-images-prod.pulse.ea.com/',
    'https://drop-assets.ea.com/',
)
