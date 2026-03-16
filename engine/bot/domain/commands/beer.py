import random
import re

import httpx
import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

SEARCH_URL = 'https://world.openfoodfacts.net/cgi/search.pl'
PAGE_SIZE = 20
MAX_PAGE = 200


class BeerCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='cerveja', flags=['show', 'dm'], category='aleatórias')

    @property
    def menu_description(self) -> str:
        return 'Receba uma cerveja aleatória com imagem.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            beer = await self._get_random_beer()
            lines = [f'🍺 *{beer["name"]}*', f'🏭 _{beer["brand"]}_']

            drink_parts: list[str] = []
            if beer.get('alcohol') is not None:
                drink_parts.append(f'{beer["alcohol"]}%')
            if beer.get('quantity'):
                drink_parts.append(beer['quantity'])
            if drink_parts:
                lines.append(f'🍷 {" · ".join(drink_parts)}')

            if beer.get('origin'):
                lines.append(f'📍 _{beer["origin"]}_')
            if beer.get('sold_in'):
                lines.append(f'🌍 _{beer["sold_in"]}_')
            if beer.get('ingredients'):
                lines.append(f'\n> {beer["ingredients"]}')

            return [Reply.to(data).image(beer['image_url'], '\n'.join(lines))]
        except Exception:
            logger.exception('beer_fetch_error')
            return [Reply.to(data).text('Erro ao buscar cerveja. Tente novamente mais tarde! 🍺')]

    async def _get_random_beer(self) -> dict:
        page = random.randint(1, MAX_PAGE)  # noqa: S311
        try:
            return await self._fetch_beer_from_page(page)
        except (ValueError, httpx.HTTPError):
            retry_page = random.randint(1, 50)  # noqa: S311
            return await self._fetch_beer_from_page(retry_page)

    async def _fetch_beer_from_page(self, page: int) -> dict:
        response = await HttpClient.get(
            SEARCH_URL,
            params={
                'action': 'process',
                'tagtype_0': 'categories',
                'tag_contains_0': 'contains',
                'tag_0': 'beers',
                'page_size': PAGE_SIZE,
                'page': page,
                'json': 1,
            },
        )
        response.raise_for_status()
        all_products = response.json()['products']
        products = [p for p in all_products if p.get('product_name') and p.get('image_front_url')]

        if not products:
            msg = 'Nenhuma cerveja encontrada'
            raise ValueError(msg)

        product = random.choice(products)  # noqa: S311
        return {
            'name': product['product_name'],
            'brand': product.get('brands', 'Desconhecida'),
            'image_url': product['image_front_url'],
            'alcohol': (product.get('nutriments') or {}).get('alcohol_100g'),
            'quantity': product.get('quantity') or None,
            'origin': self._strip_lang_prefixes(product.get('origins')),
            'sold_in': self._strip_lang_prefixes(product.get('countries')),
            'ingredients': product.get('ingredients_text') or None,
        }

    @staticmethod
    def _strip_lang_prefixes(value: str | None) -> str | None:
        if not value:
            return None
        return re.sub(r'\b[a-z]{2}:', '', value, flags=re.IGNORECASE).strip() or None
