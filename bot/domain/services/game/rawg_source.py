import random

from bot.data.game_info import GameInfo
from bot.domain.exceptions import ExternalServiceError
from bot.domain.services.game.game_source import GameSource
from bot.infrastructure.http_client import HttpClient


class RawgSource(GameSource):
    API_URL = 'https://api.rawg.io/api/games'
    MAX_PAGE = 200
    PAGE_SIZE = 40

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def fetch(self) -> GameInfo:
        page = random.randint(1, self.MAX_PAGE)  # noqa: S311
        res = await HttpClient.get(
            self.API_URL,
            params={
                'key': self._api_key,
                'ordering': '-metacritic',
                'page_size': self.PAGE_SIZE,
                'page': page,
            },
        )
        results = res.json().get('results') or []
        games = [g for g in results if g.get('background_image')]
        if not games:
            msg = 'No games with images found'
            raise ExternalServiceError(msg)

        game = random.choice(games)  # noqa: S311
        year = (game.get('released') or '?')[:4]
        genres = ', '.join(g['name'] for g in game.get('genres') or []) or '—'
        platforms = ', '.join(p['platform']['name'] for p in game.get('platforms') or []) or '—'
        metacritic = game.get('metacritic')
        rating = f'{metacritic}/100' if metacritic else None

        return GameInfo(
            name=game['name'],
            year=year,
            genres=genres,
            platforms=platforms,
            rating=rating,
            cover_url=game['background_image'],
        )
