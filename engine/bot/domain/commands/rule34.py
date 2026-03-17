import structlog
from bs4 import BeautifulSoup

from bot.data.browser_headers import BROWSER_HEADERS
from bot.data.rule34 import BANNER_URL
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class Rule34Command(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='rule 34',
            flags=['show', 'dm'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma imagem aleatória da Rule 34.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        response = await HttpClient.get(
            'https://rule34.xxx/index.php?page=post&s=random',
            timeout=30.0,
            headers=BROWSER_HEADERS,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        images: list[str] = []
        for img in soup.select('div.flexi img'):
            src = img.get('src')
            if isinstance(src, str):
                images.append(src)

        if not images:
            msg = 'Nenhuma imagem encontrada'
            raise ValueError(msg)

        url = images[1] if images[0] == BANNER_URL and len(images) > 1 else images[0]

        return [Reply.to(data).image(url, 'Aqui está a imagem que você pediu 🤗')]
