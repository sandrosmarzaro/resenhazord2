import contextlib
import random
from typing import ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    Flag,
    OptionDef,
    ParsedCommand,
    Platform,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class MovieSeriesCommand(Command):
    MAX_PAGE = 25
    ITEMS_PER_PAGE = 20
    POSTER_SIZE = 'w500'
    MOVIE_NAMES: frozenset[str] = frozenset({'filme', 'movie'})
    OMDB_BASE_URL: str = 'http://www.omdbapi.com/'
    OMDB_SOURCE_MAP: ClassVar[dict[str, str]] = {
        'Internet Movie Database': 'imdb',
        'Rotten Tomatoes': 'rt',
        'Metacritic': 'metacritic',
    }

    def __init__(self, *, tmdb_api_key: str = '', omdb_api_key: str = '') -> None:
        super().__init__()
        self._tmdb_api_key = tmdb_api_key
        self._omdb_api_key = omdb_api_key

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='filme',
            aliases=['série', 'movie', 'series'],
            options=[
                OptionDef(name='pop', pattern=r'pop\d*'),
                OptionDef(name='top', pattern=r'top\d+'),
            ],
            flags=[Flag.SHOW, Flag.DM, 'tmdb'],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um filme ou série aleatório. Use top<N> ou pop<N> para limitar o ranking.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        media_type = 'movie' if parsed.command_name in self.MOVIE_NAMES else 'tv'
        pop_str = parsed.options.get('pop', '')
        top_str = parsed.options.get('top', '')

        mode, max_page, rank_limit = self._resolve_query(pop_str, top_str)

        url = f'https://api.themoviedb.org/3/{media_type}/{mode}'
        page = random.randint(1, max_page)  # noqa: S311
        response = await HttpClient.get(
            url, params={'api_key': self._tmdb_api_key, 'language': 'pt-BR', 'page': page}
        )
        response.raise_for_status()
        results = response.json()['results']

        if rank_limit and page == max_page:
            items_on_last_page = rank_limit - (max_page - 1) * self.ITEMS_PER_PAGE
            results = results[:items_on_last_page]

        item = random.choice(results)  # noqa: S311
        poster_url = f'https://image.tmdb.org/t/p/{self.POSTER_SIZE}{item["poster_path"]}'

        genres_names = await self._fetch_genres(media_type, item.get('genre_ids', []))
        year, name = self._extract_year_and_name(media_type, item)

        ratings = await self._resolve_ratings(parsed, media_type, item)
        caption = self._build_caption(
            name=name,
            year=year,
            genres_names=genres_names,
            overview=item.get('overview', ''),
            ratings=ratings,
        )
        return [Reply.to(data).image(poster_url, caption)]

    def _resolve_query(self, pop_str: str, top_str: str) -> tuple[str, int, int]:
        if pop_str:
            mode = 'popular'
            pop_n = pop_str[3:]
            rank_limit = int(pop_n) if pop_n else 0
            max_page = (
                max(1, (rank_limit + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
                if rank_limit
                else self.MAX_PAGE
            )
        elif top_str:
            rank_limit = int(top_str[3:])
            mode = 'top_rated'
            max_page = max(1, (rank_limit + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        else:
            mode = 'popular'
            rank_limit = 0
            max_page = self.MAX_PAGE
        return mode, max_page, rank_limit

    async def _fetch_genres(self, media_type: str, genre_ids: list[int]) -> str:
        genres_url = f'https://api.themoviedb.org/3/genre/{media_type}/list'
        genres_resp = await HttpClient.get(
            genres_url, params={'api_key': self._tmdb_api_key, 'language': 'pt-BR'}
        )
        genres_resp.raise_for_status()
        genres = {g['id']: g['name'] for g in genres_resp.json()['genres']}
        return ', '.join(genres.get(gid, '?') for gid in genre_ids)

    @staticmethod
    def _extract_year_and_name(media_type: str, item: dict) -> tuple[str, str]:
        if media_type == 'movie':
            return (item.get('release_date') or '')[:4], item.get('title', '')
        return (item.get('first_air_date') or '')[:4], item.get('name', '')

    async def _resolve_ratings(
        self, parsed: ParsedCommand, media_type: str, item: dict
    ) -> dict[str, str]:
        if 'tmdb' not in parsed.flags and self._omdb_api_key:
            with contextlib.suppress(Exception):
                return await self._fetch_omdb_ratings(media_type, item['id'])
        if tmdb_avg := item.get('vote_average'):
            return {'tmdb': str(tmdb_avg)}
        return {}

    async def _fetch_omdb_ratings(self, media_type: str, tmdb_id: int) -> dict[str, str]:
        ext_url = f'https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids'
        ext_resp = await HttpClient.get(ext_url, params={'api_key': self._tmdb_api_key})
        ext_resp.raise_for_status()
        imdb_id = ext_resp.json().get('imdb_id')
        if not imdb_id:
            return {}

        omdb_resp = await HttpClient.get(
            self.OMDB_BASE_URL, params={'i': imdb_id, 'apikey': self._omdb_api_key}
        )
        omdb_resp.raise_for_status()
        data = omdb_resp.json()
        if data.get('Response') == 'False':
            return {}

        return self._parse_omdb_ratings(data.get('Ratings', []))

    def _parse_omdb_ratings(self, ratings: list[dict]) -> dict[str, str]:
        return {
            self.OMDB_SOURCE_MAP[r['Source']]: r['Value']
            for r in ratings
            if r.get('Source') in self.OMDB_SOURCE_MAP
        }

    @staticmethod
    def _build_caption(
        *, name: str, year: str, genres_names: str, overview: str, ratings: dict[str, str]
    ) -> str:
        lines: list[str] = [f'*{name}*']

        stats: list[str] = []
        if 'imdb' in ratings:
            stats.append(f'⭐ {ratings["imdb"]}')
        if 'rt' in ratings:
            stats.append(f'🍅 {ratings["rt"]}')
        if 'metacritic' in ratings:
            stats.append(f'🎬 {ratings["metacritic"]}')
        if 'tmdb' in ratings:
            stats.append(f'⭐ {ratings["tmdb"]}')
        if year:
            stats.append(f'📅 {year}')

        if stats:
            lines.append('   '.join(stats))

        if genres_names:
            lines.append(f'\n🧬 {genres_names}')

        if overview:
            lines.append(f'\n> {overview}')

        return '\n'.join(lines)
