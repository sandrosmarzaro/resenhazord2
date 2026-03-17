import anyio
import structlog

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
            category='aleatórias',
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

        desc = card['desc'].replace('\n', '')
        caption = f'*{card["name"]}*\n\n> {desc}'
        image_url = card['card_images'][0]['image_url']

        return [Reply.to(data).image(image_url, caption)]

    async def _fetch_booster_items(self) -> list[CardItem]:
        results: list[CardItem | None] = [None] * self.BOOSTER_CONFIG.count

        async def _fetch(index: int) -> None:
            response = await HttpClient.get(self.API_URL)
            response.raise_for_status()
            card = response.json()['data'][0]
            results[index] = CardItem(
                image_url=card['card_images'][0]['image_url'],
                label=card['name'],
            )

        async with anyio.create_task_group() as tg:
            for i in range(self.BOOSTER_CONFIG.count):
                tg.start_soon(_fetch, i)

        return [r for r in results if r is not None]
