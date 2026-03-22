import random

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class MovieSeriesCommand(Command):
    MAX_PAGE = 25
    POSTER_SIZE = 'w500'
    MOVIE_NAMES: frozenset[str] = frozenset({'filme', 'movie'})

    def __init__(self, *, tmdb_api_key: str = '') -> None:
        super().__init__()
        self._tmdb_api_key = tmdb_api_key

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='filme',
            aliases=['série', 'movie', 'series'],
            options=[OptionDef(name='mode', values=['top', 'pop'])],
            flags=['show', 'dm'],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba aleatoriamente um filme ou série top 500 em popularidade ou por nota.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        media_type = 'movie' if parsed.command_name in self.MOVIE_NAMES else 'tv'
        mode_value = parsed.options.get('mode')
        mode = 'top_rated' if mode_value == 'top' else 'popular'
        url = f'https://api.themoviedb.org/3/{media_type}/{mode}'

        page = random.randint(1, self.MAX_PAGE)  # noqa: S311
        response = await HttpClient.get(
            url, params={'api_key': self._tmdb_api_key, 'language': 'pt-BR', 'page': page}
        )
        response.raise_for_status()
        results = response.json()['results']
        item = random.choice(results)  # noqa: S311
        poster_url = f'https://image.tmdb.org/t/p/{self.POSTER_SIZE}{item["poster_path"]}'

        genres_url = f'https://api.themoviedb.org/3/genre/{media_type}/list'
        genres_resp = await HttpClient.get(
            genres_url, params={'api_key': self._tmdb_api_key, 'language': 'pt-BR'}
        )
        genres_resp.raise_for_status()
        genres = {g['id']: g['name'] for g in genres_resp.json()['genres']}
        genres_names = ', '.join(genres.get(gid, '?') for gid in item.get('genre_ids', []))

        if media_type == 'movie':
            year = (item.get('release_date') or '')[:4]
            name = item.get('title', '')
        else:
            year = (item.get('first_air_date') or '')[:4]
            name = item.get('name', '')

        caption = f'*{name}*\n\n'
        caption += f'🧬 {genres_names}\n'
        caption += f'⭐ {item.get("vote_average") or "Sem Nota"}   📅 {year or "Sem Data"}\n\n'
        caption += f'> {item.get("overview", "")}'

        return [Reply.to(data).image(poster_url, caption)]
