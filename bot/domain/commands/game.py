"""Random game command — IGDB (primary) with RAWG fallback."""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


@dataclass(frozen=True)
class GameInfo:
    name: str
    year: str
    genres: str
    platforms: str
    rating: str | None
    cover_url: str


class GameSource(ABC):
    @abstractmethod
    async def fetch(self) -> GameInfo: ...


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
            raise ValueError(msg)

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
            raise ValueError(msg)

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


class GameCommand(Command):
    def __init__(
        self,
        twitch_client_id: str = '',
        twitch_client_secret: str = '',
        rawg_api_key: str = '',
    ) -> None:
        super().__init__()
        self._sources: list[GameSource] = [
            IgdbSource(twitch_client_id, twitch_client_secret),
            RawgSource(rawg_api_key),
        ]

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='game',
            flags=['show', 'dm'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um jogo aleatório com capa e informações.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        for source in self._sources:
            try:
                game = await source.fetch()
                caption = self._build_caption(game)
                return [Reply.to(data).image(game.cover_url, caption)]
            except Exception:
                logger.exception('game_source_error', source=source.__class__.__name__)
                continue
        return [Reply.to(data).text('Erro ao buscar jogo. Tente novamente mais tarde! 🎮')]

    @staticmethod
    def _build_caption(game: GameInfo) -> str:
        lines = [
            f'🎮 *{game.name}* ({game.year})',
            '',
            f'🏷️ {game.genres}',
            f'🖥️ {game.platforms}',
        ]
        if game.rating:
            lines.append(f'⭐ {game.rating}')
        return '\n'.join(lines)
