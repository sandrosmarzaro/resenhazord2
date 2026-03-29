import anyio
import structlog

from bot.data.yugioh import YGO_ATTRIBUTE_EMOJIS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandConfig, ParsedCommand
from bot.domain.commands.card_booster import CardBoosterCommand, CardItem
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class YugiohCommand(CardBoosterCommand):
    API_URL = 'https://db.ygoprodeck.com/api/v7/randomcard.php'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='ygo',
            flags=['booster', 'show', 'dm'],
            category='random',
            platforms=['whatsapp', 'discord'],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta aleatória de Yu-Gi-Oh!.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'booster' in parsed.flags:
            return await self._run_booster(data, parsed)

        response = await HttpClient.get(self.API_URL)
        response.raise_for_status()
        card = response.json()['data'][0]

        caption = self._build_caption(card)
        image_url = card['card_images'][0]['image_url']

        return [Reply.to(data).image(image_url, caption)]

    @staticmethod
    def _build_caption(card: dict) -> str:
        card_type = card.get('humanReadableCardType', card.get('type', ''))
        lines: list[str] = [f'*{card["name"]}* — {card_type}']

        is_monster = 'atk' in card
        if is_monster:
            stats = f'⚔️ ATK: {card["atk"]}  🛡️ DEF: {card.get("def", "?")}'
            if 'level' in card:
                stats += f'  ⭐ Lv. {card["level"]}'
            lines.append(stats)

        meta: list[str] = []
        attr = card.get('attribute')
        if attr:
            emoji = YGO_ATTRIBUTE_EMOJIS.get(attr, '')
            meta.append(f'{emoji} {attr}' if emoji else attr)
        if is_monster and card.get('race'):
            meta.append(card['race'])
        if meta:
            lines.append('   '.join(meta))

        desc_lines = [line.strip() for line in card['desc'].strip().split('\n') if line.strip()]
        lines.append('\n> ' + '\n> '.join(desc_lines))

        return '\n'.join(lines)

    @staticmethod
    def _build_booster_label(card: dict) -> str:
        card_type = card.get('humanReadableCardType', card.get('type', ''))
        parts: list[str] = [f'*{card["name"]}*']
        if card_type:
            parts.append(card_type)
        meta: list[str] = []
        attr = card.get('attribute')
        if attr:
            emoji = YGO_ATTRIBUTE_EMOJIS.get(attr, '')
            meta.append(f'{emoji} {attr}' if emoji else attr)
        if 'atk' in card:
            meta.append(f'⚔️ {card["atk"]}')
        if meta:
            parts.append('   '.join(meta))
        return '\n'.join(parts)

    async def _fetch_booster_items(self) -> list[CardItem]:
        results: list[CardItem | None] = [None] * self.BOOSTER_CONFIG.count

        async def _fetch(index: int) -> None:
            response = await HttpClient.get(self.API_URL)
            response.raise_for_status()
            card = response.json()['data'][0]
            results[index] = CardItem(
                image_url=card['card_images'][0]['image_url'],
                label=self._build_booster_label(card),
            )

        async with anyio.create_task_group() as tg:
            for i in range(self.BOOSTER_CONFIG.count):
                tg.start_soon(_fetch, i)

        return [r for r in results if r is not None]
