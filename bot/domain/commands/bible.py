import re
from http import HTTPStatus

import httpx
import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Category,
    Command,
    CommandConfig,
    ParsedCommand,
    Platform,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class BibleCommand(Command):
    BASE_URL = 'https://bible-api.com'
    TRANSLATION = 'almeida'
    VERSE_PATTERN = re.compile(r'\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?')

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='bíblia',
            aliases=['bible'],
            args=ArgType.OPTIONAL,
            args_label='livro capítulo:versículo',
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Comando complexo. Use *,menu biblia* para detalhes.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        reference = parsed.rest.strip()
        try:
            if not reference:
                return [await self._random(data)]
            return [await self._passage(data, reference)]
        except httpx.HTTPError:
            logger.exception('upstream_failed', upstream='bible-api')
            return [
                Reply.to(data).text(
                    'A API da bíblia está fora do ar agora... 😔 Tenta de novo daqui a pouco 🙏'
                )
            ]

    async def _random(self, data: CommandData) -> BotMessage:
        response = await HttpClient.get(f'{self.BASE_URL}/data/{self.TRANSLATION}/random')
        response.raise_for_status()
        verse = response.json()['random_verse']
        title = f'{verse["book"]} {verse["chapter"]}:{verse["verse"]}'
        return Reply.to(data).text(f'*{title}*\n\n> {verse["text"].strip()}')

    async def _passage(self, data: CommandData, reference: str) -> BotMessage:
        if not self.VERSE_PATTERN.search(reference):
            return Reply.to(data).text(
                'Me manda no formato *livro capítulo:versículo*, tipo _João 3:16-18_ 🙂'
            )

        response = await HttpClient.get(
            f'{self.BASE_URL}/{reference}', params={'translation': self.TRANSLATION}
        )
        if response.status_code == HTTPStatus.NOT_FOUND:
            return Reply.to(data).text(
                'Não consegui encontrar essa passagem... 😔 Confere o livro e os versículos 🙏'
            )
        response.raise_for_status()

        passage = response.json()
        verses = '\n'.join(f'> {verse["text"].strip()}' for verse in passage['verses'])
        return Reply.to(data).text(f'*{passage["reference"]}*\n\n{verses}')
