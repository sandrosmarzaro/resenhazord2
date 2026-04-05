import random

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

    def __init__(self, *, tmdb_api_key: str = '') -> None:
        super().__init__()
        self._tmdb_api_key = tmdb_api_key

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='filme',
            aliases=['série', 'movie', 'series'],
            options=[
                OptionDef(name='pop', pattern=r'pop\d*'),
                OptionDef(name='top', pattern=r'top\d+'),
            ],
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um filme ou série aleatório. Use top<N> ou pop<N> para limitar o ranking.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        media_type = 'movie' if parsed.command_name in self.MOVIE_NAMES else 'tv'
        pop_str = parsed.options.get('pop', '')
        top_str = parsed.options.get('top', '')

        rank_limit = 0
        if pop_str:
            mode = 'popular'
            pop_n = pop_str[3:]
            if pop_n:
                rank_limit = int(pop_n)
                max_page = max(1, (rank_limit + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
            else:
                max_page = self.MAX_PAGE
        elif top_str:
            rank_limit = int(top_str[3:])
            mode = 'top_rated'
            max_page = max(1, (rank_limit + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        else:
            mode = 'popular'
            max_page = self.MAX_PAGE

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
