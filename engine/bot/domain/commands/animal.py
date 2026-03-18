"""Random animal with Wikipedia fact and image."""

import random
import re

import anyio
import httpx
import structlog

from bot.data.animal import ANIMAL_EMOJIS, ANIMAL_WIKIPEDIA_TITLES
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class AnimalCommand(Command):
    API_BASE = 'https://en.wikipedia.org/api/rest_v1/page/summary'
    USER_AGENT = 'ResenhazordBot/2.0'
    MAX_RETRIES = 3
    TIMEOUT = 10.0
    MAX_FACT_LENGTH = 300
    RATE_LIMIT_DEFAULT_WAIT = 60

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='animal',
            flags=['show', 'dm'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma foto e curiosidade de um animal aleatório.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        animal_keys = list(ANIMAL_WIKIPEDIA_TITLES.keys())
        animal_type = random.choice(animal_keys)  # noqa: S311
        wiki_title = ANIMAL_WIKIPEDIA_TITLES[animal_type]

        try:
            animal_data = await self._fetch_with_rate_limit(wiki_title)
            if not animal_data:
                return []

            fact = self._extract_fact(animal_data['extract'])
            emoji = ANIMAL_EMOJIS[animal_type]
            name = self._format_name(animal_type)
            caption = f'*{emoji} {name}*\n\n📝 {fact}'

            thumbnail = animal_data.get('thumbnail')
            if not thumbnail:
                return [Reply.to(data).text(caption)]

            buffer = await HttpClient.get_buffer(
                thumbnail['source'],
                headers={'User-Agent': self.USER_AGENT},
            )
            return [Reply.to(data).image_buffer(buffer, caption)]
        except Exception:
            logger.exception('animal_command_error')
            return [Reply.to(data).text('Erro ao buscar animal. Tente novamente mais tarde! 🐾')]

    async def _fetch_with_rate_limit(self, wiki_title: str) -> dict | None:
        for _ in range(self.MAX_RETRIES + 1):
            try:
                response = await HttpClient.get(
                    f'{self.API_BASE}/{wiki_title}',
                    timeout=self.TIMEOUT,
                    headers={'User-Agent': self.USER_AGENT},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:  # noqa: PLR2004
                    retry_after = exc.response.headers.get('retry-after')
                    wait_seconds = int(retry_after) if retry_after else self.RATE_LIMIT_DEFAULT_WAIT
                    await anyio.sleep(wait_seconds)
                    continue
                raise
        return None

    @staticmethod
    def _format_name(animal_type: str) -> str:
        return ' '.join(word.capitalize() for word in animal_type.split('_'))

    @classmethod
    def _extract_fact(cls, extract: str) -> str:
        sentences = re.findall(r'[^.!?]*[.!?]+', extract) or [extract]
        fact = ''.join(sentences[:2]).strip()
        if len(fact) > cls.MAX_FACT_LENGTH:
            return sentences[0].strip()
        return fact
