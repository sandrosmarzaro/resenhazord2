import random
from datetime import UTC, datetime

from bot.data.game_info import GameInfo
from bot.domain.exceptions import ExternalServiceError
from bot.domain.services.game.game_source import GameSource
from bot.infrastructure.http_client import HttpClient


class IgdbSource(GameSource):
    TOKEN_URL = 'https://id.twitch.tv/oauth2/token'  # noqa: S105
    GAMES_URL = 'https://api.igdb.com/v4/games'
    COVER_BASE = 'https://images.igdb.com/igdb/image/upload/t_cover_big_2x'
    MAX_OFFSET = 2000

    _access_token: str | None = None

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    async def _get_token(self) -> str:
        if IgdbSource._access_token:
            return IgdbSource._access_token

        res = await HttpClient.post(
            self.TOKEN_URL,
            params={
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'client_credentials',
            },
        )
        token = res.json()['access_token']
        IgdbSource._access_token = token
        return token

    async def fetch(self) -> GameInfo:
        token = await self._get_token()
        offset = random.randint(0, self.MAX_OFFSET)  # noqa: S311
        body = (
            'fields name,first_release_date,genres.name,'
            'platforms.name,total_rating,cover.image_id;'
            ' where total_rating_count > 100 & cover != null;'
            f' sort total_rating_count desc; offset {offset}; limit 1;'
        )
        res = await HttpClient.post(
            self.GAMES_URL,
            content=body,
            headers={
                'Client-ID': self._client_id,
                'Authorization': f'Bearer {token}',
                'Content-Type': 'text/plain',
            },
        )
        games = res.json()
        if not games:
            msg = 'No game returned from IGDB'
            raise ExternalServiceError(msg)

        game = games[0]
        release_ts = game.get('first_release_date')
        year = str(datetime.fromtimestamp(release_ts, tz=UTC).year) if release_ts else '?'
        genres = ', '.join(g['name'] for g in game.get('genres') or []) or '—'
        platforms = ', '.join(p['name'] for p in game.get('platforms') or []) or '—'
        total_rating = game.get('total_rating')
        rating = f'{round(total_rating)}/100' if total_rating else None
        cover_url = f'{self.COVER_BASE}/{game["cover"]["image_id"]}.jpg'

        return GameInfo(
            name=game['name'],
            year=year,
            genres=genres,
            platforms=platforms,
            rating=rating,
            cover_url=cover_url,
        )

    @classmethod
    def reset_token(cls) -> None:
        cls._access_token = None
