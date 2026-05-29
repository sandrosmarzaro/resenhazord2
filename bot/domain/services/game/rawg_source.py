import random
from typing import Any

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
        page = random.randint(1, self.MAX_PAGE)
        res = await HttpClient.get(
            self.API_URL,
            params={
                'key': self._api_key,
                'ordering': '-metacritic',
                'page_size': self.PAGE_SIZE,
                'page': page,
            },
        )
        results: list[dict[str, Any]] = res.json().get('results') or []
        games = [g for g in results if g.get('background_image')]
        if not games:
            msg = 'No games with images found'
            raise ExternalServiceError(msg)

        game = random.choice(games)
        return self._parse_game(game)

    @staticmethod
    def _parse_game(game: dict) -> GameInfo:
        year = (game.get('released') or '?')[:4]
        genres = RawgSource._join_names(game.get('genres') or [], 'name', '—')
        platforms = RawgSource._join_nested(game.get('platforms') or [], 'platform', 'name', '—')
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

    @staticmethod
    def _join_names(items: list[dict], key: str, fallback: str) -> str:
        result = ', '.join(item[key] for item in items)
        return result or fallback

    @staticmethod
    def _join_nested(items: list[dict], outer_key: str, inner_key: str, fallback: str) -> str:
        result = ', '.join(item[outer_key][inner_key] for item in items)
        return result or fallback
