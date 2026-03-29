import random

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class MyAnimeListCommand(Command):
    DEFAULT_MAX_PAGE = 20
    MAX_TOP = 500
    ITEMS_PER_PAGE = 25

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='anime',
            aliases=['manga'],
            flags=['show', 'dm'],
            options=[OptionDef(name='top', pattern=r'top\d+')],
            category='random',
            platforms=['whatsapp', 'discord'],
        )

    @property
    def menu_description(self) -> str:
        return (
            f'Receba um anime ou mangá aleatório. '
            f'Use top1-top{self.MAX_TOP} para limitar o ranking.'
        )

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        base_url = 'https://api.jikan.moe/v4'
        media_type = 'anime' if parsed.command_name == 'anime' else 'manga'

        top_str = parsed.options.get('top', '')
        if top_str:
            n = int(top_str[3:])
            if not 1 <= n <= self.MAX_TOP:
                return [Reply.to(data).text(f'Use top1 até top{self.MAX_TOP}. 📊')]
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
