import random

import structlog

from bot.data.clash_royale import RARITY_EMOJIS, TYPE_EMOJIS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class ClashRoyaleCommand(Command):
    CARDS_URL = 'https://royaleapi.github.io/cr-api-data/json/cards.json'
    ASSETS_BASE = 'https://raw.githubusercontent.com/RoyaleAPI/cr-api-assets/master/cards/'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='cr',
            flags=['show', 'dm'],
            category='random',
            platforms=['whatsapp', 'discord'],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta aleatória de Clash Royale.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
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
