import random

import structlog

from bot.data.clash_royale import RARITY_EMOJIS, TYPE_EMOJIS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.commands.card_booster import BoosterConfig, CardBoosterCommand, CardItem
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

DECK_SIZE = 8
DECK_COLUMNS = 4


class ClashRoyaleCommand(CardBoosterCommand):
    CARDS_URL = 'https://royaleapi.github.io/cr-api-data/json/cards.json'
    ASSETS_BASE = 'https://raw.githubusercontent.com/RoyaleAPI/cr-api-assets/master/cards/'
    BOOSTER_CONFIG = BoosterConfig(
        count=DECK_SIZE, columns=DECK_COLUMNS, cell_width=250, cell_height=330
    )

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='cr',
            aliases=['clashroyale'],
            flags=['deck', Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta aleatória de Clash Royale.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'deck' in parsed.flags:
            return await self._run_booster(data, parsed)

        try:
            response = await HttpClient.get(self.CARDS_URL)
            response.raise_for_status()
            cards = response.json()
            card = random.choice(cards)  # noqa: S311

            image_url = f'{self.ASSETS_BASE}{card["key"]}.png'
            rarity_emoji = RARITY_EMOJIS.get(card['rarity'], '❓')
            type_emoji = TYPE_EMOJIS.get(card['type'], '❓')

            stats = (
                f'⚡ {card["elixir"]}   {type_emoji} {card["type"]}'
                f'   {rarity_emoji} {card["rarity"]}'
            )
            lines = [
                f'*{card["name"]}*',
                '',
                stats,
                f'🏟️ Arena {card["arena"]}',
                '',
                f'> {card["description"]}',
            ]

            return [Reply.to(data).image(image_url, '\n'.join(lines))]
        except Exception:
            logger.exception('clash_royale_fetch_error')
            return [
                Reply.to(data).text(
                    'Erro ao buscar carta de Clash Royale. Tente novamente mais tarde! ⚔️'
                )
            ]

    async def _fetch_booster_items(self) -> list[CardItem]:
        response = await HttpClient.get(self.CARDS_URL)
        response.raise_for_status()
        cards = response.json()
        chosen = random.sample(cards, min(DECK_SIZE, len(cards)))
        return [
            CardItem(
                image_url=f'{self.ASSETS_BASE}{card["key"]}.png',
                label=(
                    f'{card["name"]} {RARITY_EMOJIS.get(card["rarity"], "❓")} ⚡{card["elixir"]}'
                ),
            )
            for card in chosen
        ]
