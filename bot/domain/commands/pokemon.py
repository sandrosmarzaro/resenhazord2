import random

import structlog

from bot.data.pokemon_type_emojis import POKEMON_TYPE_EMOJIS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, CommandConfig, Flag, ParsedCommand, Platform
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
            flags=['team', Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
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

        stats = {s['stat']['name']: s['base_stat'] for s in pokemon['stats']}
        height = pokemon['height'] / 10
        weight = pokemon['weight'] / 10
        caption = (
            f'*{name}* — {types}\n\n'
            f'📖 #{pokemon["id"]}   📏 {height:.1f}m   ⚖️ {weight:.1f}kg\n'
            f'❤️ {stats.get("hp", "?")}   '
            f'⚔️ {stats.get("attack", "?")}   '
            f'🛡️ {stats.get("defense", "?")}   '
            f'⚡ {stats.get("speed", "?")}'
        )
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
