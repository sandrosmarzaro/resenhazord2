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


class MyAnimeListCommand(Command):
    DEFAULT_MAX_PAGE: ClassVar[int] = 20
    ITEMS_PER_PAGE: ClassVar[int] = 25
    _FALLBACK_UNKNOWN: ClassVar[str] = 'Desconhecido'

    _MEDIA_PROFILES: ClassVar[dict[str, dict]] = {
        'anime': {
            'creator_key': 'studios',
            'date_key': 'aired',
            'size_key': 'episodes',
            'creator_emoji': '🎙️',
            'size_emoji': '🎥',
        },
        'manga': {
            'creator_key': 'authors',
            'date_key': 'published',
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

        page = random.randint(1, max_page)  # noqa: S311
        params: dict[str, str | int] = {'page': page}
        if pop_mode:
            params['filter'] = 'bypopularity'

        response = await HttpClient.get(
            f'https://api.jikan.moe/v4/top/{media_type}', params=params
        )
        response.raise_for_status()
        items = response.json()['data']

        if top_n and page == max_page:
            items = items[: top_n - (max_page - 1) * self.ITEMS_PER_PAGE]

        item = random.choice(items)  # noqa: S311
        profile = self._MEDIA_PROFILES[media_type]
        caption = self._build_caption(item, profile)
        image = item['images']['webp']['large_image_url']
        return [Reply.to(data).image(image, caption)]

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
        creators = cls._join_names(item, profile['creator_key'])
        genres = cls._join_names(item, 'genres')
        themes = cls._join_names(item, 'themes')
        demos = cls._join_names(item, 'demographics')
        release_date = cls._extract_year(item, profile['date_key'])
        size = item.get(profile['size_key'])

        size_display = f'{size}x' if size else '?'
        date_display = str(release_date) if release_date else '?'
        score_display = str(item.get('score')) if item.get('score') else '?'
        rank_display = str(item.get('rank')) if item.get('rank') else '?'

        return '\n'.join(
            [
                f'*{item["title"]}*',
                '',
                f'{profile["size_emoji"]} {size_display} \t📅 {date_display}',
                f'⭐️ {score_display} \t🏆 #{rank_display}',
                f'🧬 {genres}',
                f'📜 {themes}',
                f'📈 {demos}',
                f'{profile["creator_emoji"]} {creators}',
            ]
        )

    @classmethod
    def _join_names(cls, item: dict, key: str) -> str:
        names = ', '.join(entry['name'] for entry in item.get(key, []))
        return names or cls._FALLBACK_UNKNOWN

    @staticmethod
    def _extract_year(item: dict, date_key: str) -> int | None:
        return item.get(date_key, {}).get('prop', {}).get('from', {}).get('year')
