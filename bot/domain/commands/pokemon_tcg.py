import anyio
import structlog

from bot.data.pokemon_type_emojis import POKEMON_TYPE_EMOJIS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandConfig, ParsedCommand
from bot.domain.commands.card_booster import CardBoosterCommand, CardItem
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class PokemonTCGCommand(CardBoosterCommand):
    BASE_URL = 'https://api.tcgdex.net/v2/en'
    TIMEOUT = 30.0
    MAX_RETRIES = 3

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='pokémontcg',
            aliases=['ptcg'],
            flags=['booster', 'show', 'dm'],
            category='random',
            platforms=['whatsapp', 'discord'],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta aleatória do Pokémon TCG.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'booster' in parsed.flags:
            return await self._run_booster(data, parsed)

        try:
            card = await self._fetch_card_with_image()
            if not card:
                logger.warning('pokemon_tcg_no_image_after_retries')
                return [
                    Reply.to(data).text(
                        'Não foi possível encontrar uma carta com imagem. Tente novamente.'
                    )
                ]

            caption = self._build_caption(card)
            image_buffer = await HttpClient.get_buffer(
                f'{card["image"]}/high.webp', timeout=self.TIMEOUT
            )
            return [Reply.to(data).image_buffer(image_buffer, caption)]
        except Exception:
            logger.exception('pokemon_tcg_error')
            return [
                Reply.to(data).text(
                    'Não foi possível buscar uma carta no momento. Tente novamente.'
                )
            ]

    async def _fetch_card_with_image(self) -> dict | None:
        for _ in range(self.MAX_RETRIES):
            response = await HttpClient.get(f'{self.BASE_URL}/random/card', timeout=self.TIMEOUT)
            response.raise_for_status()
            card = response.json()
            if card.get('image'):
                return card
        return None

    async def _fetch_booster_items(self) -> list[CardItem]:
        results: list[CardItem | None] = [None] * self.BOOSTER_CONFIG.count

        async def _fetch(index: int) -> None:
            card = await self._fetch_single_card()
            results[index] = CardItem(
                image_url=f'{card["image"]}/high.webp',
                label=self._build_booster_label(card),
            )

        async with anyio.create_task_group() as tg:
            for i in range(self.BOOSTER_CONFIG.count):
                tg.start_soon(_fetch, i)

        return [r for r in results if r is not None]

    async def _fetch_single_card(self) -> dict:
        for _ in range(self.MAX_RETRIES):
            response = await HttpClient.get(f'{self.BASE_URL}/random/card', timeout=self.TIMEOUT)
            response.raise_for_status()
            card = response.json()
            if card.get('image'):
                return card
        msg = 'PokemonTCG: no card with image after retries'
        raise ExternalServiceError(msg)

    def _type_emojis(self, card: dict) -> str:
        types: list[str] = card.get('types') or []
        return ' '.join(POKEMON_TYPE_EMOJIS.get(t.lower(), t) for t in types)

    def _build_booster_label(self, card: dict) -> str:
        type_emojis = self._type_emojis(card)
        parts: list[str] = [f'*{card["name"]}*']

        stage = f' {card["stage"]}' if card.get('stage') else ''
        parts.append(f'{card["category"]}{stage}')

        stats = [f'HP: {card["hp"]}' if card.get('hp') else '', type_emojis]
        stats_line = ' '.join(s for s in stats if s)
        if stats_line:
            parts.append(stats_line)

        if card.get('rarity'):
            parts.append(f'⭐ {card["rarity"]}')

        return '\n'.join(parts)

    def _build_caption(self, card: dict) -> str:
        type_emojis = self._type_emojis(card)

        stage = f' {card["stage"]}' if card.get('stage') else ''
        lines: list[str] = [f'*{card["name"]}* — {card["category"]}{stage}']

        stats = [
            f'❤️ HP: {card["hp"]}' if card.get('hp') else '',
            f'⚡ {type_emojis}' if type_emojis else '',
        ]
        stats_line = '   '.join(s for s in stats if s)
        if stats_line:
            lines.append(stats_line)

        lines.append('')
        card_set = card['set']
        lines.append(
            f'📦 {card_set["name"]} #{card["localId"]}/{card_set["cardCount"]["official"]}'
        )
        if card.get('rarity'):
            lines.append(f'⭐ {card["rarity"]}')
        if card.get('illustrator'):
            lines.append(f'🎨 {card["illustrator"]}')

        return '\n'.join(lines)
