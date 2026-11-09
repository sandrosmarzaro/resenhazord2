import random
import re
from http import HTTPStatus
from typing import ClassVar

import httpx
import structlog

from bot.data.bible import BIBLE_CHAPTERS
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
    CHAPTER_URL = 'https://api.getbible.net/v2/livre'
    QUERY_URL = 'https://query.getbible.net/v2/livre'
    VERSE_PATTERN = re.compile(r'\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?')
    SEPARATOR_SPACES = re.compile(r'\s*([:-])\s*')
    # Codes getbible answers a reference it can't resolve with, unlike a missing translation.
    BAD_REFERENCE_CODES: ClassVar[frozenset[str]] = frozenset({'invalid_reference', 'not_found'})

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
            logger.exception('upstream_failed', upstream='getbible')
            return [
                Reply.to(data).text(
                    'A API da bíblia está fora do ar agora... 😔 Tenta de novo daqui a pouco 🙏'
                )
            ]

    async def _random(self, data: CommandData) -> BotMessage:
        book = random.choices(list(BIBLE_CHAPTERS), weights=list(BIBLE_CHAPTERS.values()))[0]
        chapter = random.randint(1, BIBLE_CHAPTERS[book])
        response = await HttpClient.get(f'{self.CHAPTER_URL}/{book}/{chapter}.json')
        response.raise_for_status()
        verse = random.choice(response.json()['verses'])
        return Reply.to(data).text(f'*{verse["name"]}*\n\n> {verse["text"].strip()}')

    async def _passage(self, data: CommandData, reference: str) -> BotMessage:
        if not self.VERSE_PATTERN.search(reference):
            return Reply.to(data).text(
                'Me manda no formato *livro capítulo:versículo*, tipo _João 3:16-18_ 🙂'
            )

        response = await HttpClient.get(
            f'{self.QUERY_URL}/{self.SEPARATOR_SPACES.sub(r"\1", reference)}'
        )
        if response.status_code == HTTPStatus.NOT_FOUND and self._is_bad_reference(response):
            return Reply.to(data).text(
                'Não consegui encontrar essa passagem... 😔 Confere o livro e os versículos 🙏'
            )
        response.raise_for_status()

        return Reply.to(data).text('\n\n'.join(map(self._render, response.json().values())))

    def _is_bad_reference(self, response: httpx.Response) -> bool:
        try:
            return response.json().get('code') in self.BAD_REFERENCE_CODES
        except ValueError:
            return False

    @staticmethod
    def _render(chapter: dict) -> str:
        verses = '\n'.join(f'> {verse["text"].strip()}' for verse in chapter['verses'])
        span = chapter['ref'][0].rpartition(' ')[2]
        return f'*{chapter["book_name"]} {span}*\n\n{verses}'
