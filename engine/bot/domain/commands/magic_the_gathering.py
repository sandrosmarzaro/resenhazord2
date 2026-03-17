import math
import random

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandConfig, ParsedCommand
from bot.domain.commands.card_booster import CardBoosterCommand, CardItem
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class MagicTheGatheringCommand(CardBoosterCommand):
    API_URL = 'https://api.magicthegathering.io/v1/cards'
    PAGE_SIZE = 100
    MAX_RETRIES = 5

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='mtg',
            flags=['booster', 'show', 'dm'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta aleatória de Magic: The Gathering.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'booster' in parsed.flags:
            return await self._run_booster(data, parsed)

        total_pages = await self._fetch_total_pages()
        card = await self._fetch_single_card(total_pages)

        caption = f'*{card["name"]}*\n\n> {card.get("text", "")}'
        return [Reply.to(data).image(card['imageUrl'], caption)]

    async def _fetch_total_pages(self) -> int:
        response = await HttpClient.get(f'{self.API_URL}?pageSize={self.PAGE_SIZE}')
        response.raise_for_status()
        total_count = int(response.headers['total-count'])
        return math.ceil(total_count / self.PAGE_SIZE)

    async def _fetch_single_card(self, total_pages: int) -> dict:
        for _ in range(self.MAX_RETRIES):
            page = random.randint(1, total_pages)  # noqa: S311
            response = await HttpClient.get(f'{self.API_URL}?pageSize={self.PAGE_SIZE}&page={page}')
            response.raise_for_status()
            cards = response.json()['cards']

            candidates = [
                c for c in cards if c.get('imageUrl') and 'multiverseid=0' not in c['imageUrl']
            ]
            if not candidates:
                continue

            card = random.choice(candidates)  # noqa: S311

            head_resp = await HttpClient.get(card['imageUrl'], follow_redirects=True)
            if 'card_back' not in str(head_resp.url):
                return card

        msg = 'MTG: no card with image after retries'
        raise ValueError(msg)

    async def _fetch_booster_items(self) -> list[CardItem]:
        total_pages = await self._fetch_total_pages()
        items: list[CardItem] = []
        for _ in range(self.BOOSTER_CONFIG.count):
            card = await self._fetch_single_card(total_pages)
            items.append(
                CardItem(
                    image_url=card['imageUrl'],
                    label=card['name'],
                )
            )
        return items
