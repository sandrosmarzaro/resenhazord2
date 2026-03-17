import structlog
from bs4 import BeautifulSoup

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

BANNER_URL = 'https://kanako.store/products/futa-body'


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
