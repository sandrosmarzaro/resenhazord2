import random
from typing import ClassVar

from bot.data.anilist import ANILIST_AUTHOR_ROLE_PREFIXES, ANILIST_MEDIA_QUERY
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


class MyAnimeListCommand(Command):
    ANILIST_URL: ClassVar[str] = 'https://graphql.anilist.co'
    DEFAULT_MAX_PAGE: ClassVar[int] = 20
    ITEMS_PER_PAGE: ClassVar[int] = 25
    MAX_THEMES: ClassVar[int] = 3
    SCORE_SCALE: ClassVar[int] = 10
    _FALLBACK_UNKNOWN: ClassVar[str] = 'Desconhecido'

    _MEDIA_PROFILES: ClassVar[dict[str, dict]] = {
        'anime': {
            'creator_key': 'studios',
            'size_key': 'episodes',
            'creator_emoji': '🎙️',
            'size_emoji': '🎥',
        },
        'manga': {
            'creator_key': 'staff',
            'size_key': 'chapters',
            'creator_emoji': '🖋',
            'size_emoji': '📚',
        },
    }

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='anime',
            aliases=['manga'],
            flags=[Flag.SHOW, Flag.DM],
            options=[
                OptionDef(name='pop', pattern=r'pop\d*'),
                OptionDef(name='top', pattern=r'top\d+'),
            ],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um anime ou mangá aleatório. Use top<N> ou pop<N> para limitar o ranking.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        media_type = 'anime' if parsed.command_name == 'anime' else 'manga'
        pop_mode = 'pop' in parsed.options
        top_n, max_page = self._resolve_page_range(parsed)

        page = random.randint(1, max_page)
        response = await HttpClient.post(
            self.ANILIST_URL,
            json={
                'query': ANILIST_MEDIA_QUERY,
                'variables': {
                    'page': page,
                    'perPage': self.ITEMS_PER_PAGE,
                    'type': media_type.upper(),
                    'sort': ['POPULARITY_DESC' if pop_mode else 'SCORE_DESC'],
                },
            },
        )
        response.raise_for_status()
        items = response.json()['data']['Page']['media']

        if top_n and page == max_page:
            items = items[: top_n - (max_page - 1) * self.ITEMS_PER_PAGE]

        item = random.choice(items)
        profile = self._MEDIA_PROFILES[media_type]
        caption = self._build_caption(item, profile)
        return [Reply.to(data).image(item['coverImage']['extraLarge'], caption)]

    def _resolve_page_range(self, parsed: ParsedCommand) -> tuple[int, int]:
        if 'pop' in parsed.options:
            pop_str = parsed.options['pop']
            pop_n = pop_str.removeprefix('pop')
            if pop_n:
                rank_limit = int(pop_n)
                return rank_limit, max(
                    1, (rank_limit + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
                )
            return 0, self.DEFAULT_MAX_PAGE

        top_str = parsed.options.get('top', '')
        if not top_str:
            return 0, self.DEFAULT_MAX_PAGE
        top_n = int(top_str.removeprefix('top'))
        return top_n, max(1, (top_n + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)

    @classmethod
    def _build_caption(cls, item: dict, profile: dict) -> str:
        tags = item.get('tags') or []
        themes = [tag['name'] for tag in tags if tag['category'].startswith('Theme-')]
        demographics = [tag['name'] for tag in tags if tag['category'] == 'Demographic']
        size = item.get(profile['size_key'])
        year = (item.get('startDate') or {}).get('year')
        score = item.get('averageScore')
        rank = cls._rated_rank(item)
        creators = cls._creators(item, profile['creator_key'])

        size_display = f'{size}x' if size else '?'
        date_display = str(year) if year else '?'
        score_display = str(score / cls.SCORE_SCALE) if score else '?'
        rank_display = str(rank) if rank else '?'

        return '\n'.join(
            [
                f'*{item["title"]["romaji"]}*',
                '',
                f'{profile["size_emoji"]} {size_display} \t📅 {date_display}',
                f'⭐️ {score_display} \t🏆 #{rank_display}',
                f'🧬 {cls._join(item.get("genres") or [])}',
                f'📜 {cls._join(themes[: cls.MAX_THEMES])}',
                f'📈 {cls._join(demographics)}',
                f'{profile["creator_emoji"]} {cls._join(creators)}',
            ]
        )

    @staticmethod
    def _rated_rank(item: dict) -> int | None:
        rankings = item.get('rankings') or []
        rated = (r['rank'] for r in rankings if r['type'] == 'RATED' and r['allTime'])
        return next(rated, None)

    @staticmethod
    def _creators(item: dict, creator_key: str) -> list[str]:
        if creator_key == 'studios':
            return [node['name'] for node in item['studios']['nodes']]
        return [
            edge['node']['name']['full']
            for edge in item['staff']['edges']
            if edge['role'].startswith(ANILIST_AUTHOR_ROLE_PREFIXES)
        ]

    @classmethod
    def _join(cls, names: list[str]) -> str:
        return ', '.join(names) or cls._FALLBACK_UNKNOWN
