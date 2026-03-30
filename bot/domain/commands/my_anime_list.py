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


class MyAnimeListCommand(Command):
    DEFAULT_MAX_PAGE = 20
    ITEMS_PER_PAGE = 25

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='anime',
            aliases=['manga'],
            flags=[Flag.SHOW, Flag.DM],
            options=[OptionDef(name='top', pattern=r'top\d+')],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um anime ou mangá aleatório. Use top<N> para limitar o ranking.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        base_url = 'https://api.jikan.moe/v4'
        media_type = 'anime' if parsed.command_name == 'anime' else 'manga'

        top_str = parsed.options.get('top', '')
        if top_str:
            n = int(top_str[3:])
            max_page = max(1, (n + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        else:
            max_page = self.DEFAULT_MAX_PAGE

        page = random.randint(1, max_page)  # noqa: S311

        response = await HttpClient.get(f'{base_url}/top/{media_type}', params={'page': page})
        response.raise_for_status()
        items = response.json()['data']
        item = random.choice(items)  # noqa: S311

        image = item['images']['webp']['large_image_url']
        genres = ', '.join(g['name'] for g in item.get('genres', []))
        themes = ', '.join(t['name'] for t in item.get('themes', []))
        demos = ', '.join(d['name'] for d in item.get('demographics', []))

        if media_type == 'anime':
            creator_emoji = '🎙️'
            creators = ', '.join(s['name'] for s in item.get('studios', []))
            release_date = item.get('aired', {}).get('prop', {}).get('from', {}).get('year')
            size = item.get('episodes')
            size_emoji = '🎥'
        else:
            creator_emoji = '🖋'
            creators = ', '.join(a['name'] for a in item.get('authors', []))
            release_date = item.get('published', {}).get('prop', {}).get('from', {}).get('year')
            size = item.get('chapters')
            size_emoji = '📚'

        caption = f'*{item["title"]}*\n\n'
        caption += f'{size_emoji} {size or "?"}x \t📅 {release_date or "?"}\n'
        caption += f'⭐️ {item.get("score") or "?"} \t🏆 #{item.get("rank") or "?"}\n'
        caption += f'🧬 {genres or "Desconhecido"}\n'
        caption += f'📜 {themes or "Desconhecido"}\n'
        caption += f'📈 {demos or "Desconhecido"}\n'
        caption += f'{creator_emoji} {creators or "Desconhecido"}'

        return [Reply.to(data).image(image, caption)]
