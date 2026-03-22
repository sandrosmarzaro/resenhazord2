import math
import random

import anyio
import structlog

from bot.data.mtg_symbols import replace_mana_symbols
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandConfig, ParsedCommand
from bot.domain.commands.card_booster import CardBoosterCommand, CardItem
from bot.domain.exceptions import ExternalServiceError
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
            aliases=['magic'],
            flags=['booster', 'show', 'dm'],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta aleatória de Magic: The Gathering.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            if 'booster' in parsed.flags:
                return await self._run_booster(data, parsed)

            total_pages = await self._fetch_total_pages()
            card = await self._fetch_single_card(total_pages)

            caption = self._build_caption(card)
            return [Reply.to(data).image(card['imageUrl'], caption)]
        except Exception:
            logger.exception('mtg_fetch_error')
            return [
                Reply.to(data).text('Erro ao buscar carta de MTG. Tente novamente mais tarde! 🃏')
            ]

    @staticmethod
    def _build_caption(card: dict) -> str:
        card_type = card.get('type', '')
        lines: list[str] = [f'*{card["name"]}* — {card_type}']

        meta: list[str] = []
        if card.get('rarity'):
            meta.append(f'💎 {card["rarity"]}')
        if card.get('manaCost'):
            meta.append(replace_mana_symbols(card['manaCost']))
        if meta:
            lines.append('   '.join(meta))

        if card.get('power') is not None and card.get('toughness') is not None:
            lines.append(f'⚔️ {card["power"]}/{card["toughness"]}')

        text = card.get('text', '')
        if text:
            lines.append(f'\n> {replace_mana_symbols(text)}')

        return '\n'.join(lines)

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
        raise ExternalServiceError(msg)

    @staticmethod
    def _build_booster_label(card: dict) -> str:
        parts: list[str] = [card['name']]
        if card.get('type'):
            parts.append(card['type'])
        meta: list[str] = []
        if card.get('rarity'):
            meta.append(f'💎 {card["rarity"]}')
        if card.get('manaCost'):
            meta.append(replace_mana_symbols(card['manaCost']))
        if meta:
            parts.append('   '.join(meta))
        return '\n'.join(parts)

    async def _fetch_booster_items(self) -> list[CardItem]:
        total_pages = await self._fetch_total_pages()
        results: list[CardItem | None] = [None] * self.BOOSTER_CONFIG.count

        async def _fetch(index: int) -> None:
            card = await self._fetch_single_card(total_pages)
            results[index] = CardItem(
                image_url=card['imageUrl'],
                label=self._build_booster_label(card),
            )

        async with anyio.create_task_group() as tg:
            for i in range(self.BOOSTER_CONFIG.count):
                tg.start_soon(_fetch, i)

        return [r for r in results if r is not None]
