"""Random Pokémon command — single random or team of 6."""

import random

import structlog

from bot.data.pokemon_type_emojis import POKEMON_TYPE_EMOJIS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandConfig, ParsedCommand
from bot.domain.commands.card_booster import BoosterConfig, CardBoosterCommand, CardItem
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class PokemonCommand(CardBoosterCommand):
    BASE_URL = 'https://pokeapi.co/api/v2/pokemon/'
    MAX_POKEMON_ID = 1025
    BOOSTER_CONFIG = BoosterConfig(
        count=6,
        columns=3,
        cell_width=475,
        cell_height=475,
    )

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='pokémon',
            flags=['team', 'show', 'dm'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma imagem e dados de um pokémon aleatório.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'team' in parsed.flags:
            return await self._run_booster(data, parsed)
        return await self._run_single(data)

    async def _fetch_booster_items(self) -> list[CardItem]:
        ids = [random.randint(1, self.MAX_POKEMON_ID) for _ in range(self.BOOSTER_CONFIG.count)]  # noqa: S311
        items: list[CardItem] = []
        for pokemon_id in ids:
            response = await HttpClient.get(f'{self.BASE_URL}{pokemon_id}')
            pokemon = response.json()
            name = pokemon['name'].capitalize()
            types = self._format_types(pokemon['types'])
            image_url = self._resolve_image(pokemon)
            items.append(CardItem(image_url=image_url, label=f'{name} {types} (#{pokemon["id"]})'))
        return items

    async def _run_single(self, data: CommandData) -> list[BotMessage]:
        pokemon_id = random.randint(1, self.MAX_POKEMON_ID)  # noqa: S311
        response = await HttpClient.get(f'{self.BASE_URL}{pokemon_id}')
        pokemon = response.json()

        name = pokemon['name'].capitalize()
        types = self._format_types(pokemon['types'])
        image_url = self._resolve_image(pokemon)

        caption = f'*{name}* — {types}\n\n📖 Pokédex #{pokemon["id"]}'
        buffer = await HttpClient.get_buffer(image_url)
        return [Reply.to(data).image_buffer(buffer, caption)]

    @staticmethod
    def _format_types(types: list[dict]) -> str:
        return ' '.join(
            POKEMON_TYPE_EMOJIS.get(str(t['type']['name']), str(t['type']['name'])) for t in types
        )

    @staticmethod
    def _resolve_image(pokemon: dict) -> str:
        return (
            pokemon['sprites']['other']['official-artwork']['front_default']
            or pokemon['sprites']['front_default']
        )
