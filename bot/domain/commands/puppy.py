import random
import re

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class PuppyCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='puppy',
            flags=['show', 'dm'],
            options=[OptionDef(name='tipo', values=['dog', 'cat'])],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma foto aleatória de cachorro ou gato.'

    @staticmethod
    def _extract_breed(image_url: str) -> str:
        match = re.search(r'breeds/([^/]+)/', image_url)
        if not match:
            return 'Dog'
        return ' '.join(word.capitalize() for word in match.group(1).split('-'))

    async def _fetch_dog(self, data: CommandData) -> list[BotMessage]:
        response = await HttpClient.get('https://dog.ceo/api/breeds/image/random')
        response.raise_for_status()
        image_url = response.json()['message']
        breed = self._extract_breed(image_url)
        buffer = await HttpClient.get_buffer(image_url)
        return [Reply.to(data).image_buffer(buffer, f'🐶 {breed}')]

    async def _fetch_cat(self, data: CommandData) -> list[BotMessage]:
        response = await HttpClient.get('https://cataas.com/cat?json=true')
        response.raise_for_status()
        image_url = response.json()['url']
        buffer = await HttpClient.get_buffer(image_url, headers={'Accept': '*/*'})
        return [Reply.to(data).image_buffer(buffer, '🐱 Cat')]

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            tipo = parsed.options.get('tipo') or random.choice(['dog', 'cat'])  # noqa: S311
            if tipo == 'dog':
                return await self._fetch_dog(data)
            return await self._fetch_cat(data)
        except Exception:
            logger.exception('puppy_fetch_error')
            return [Reply.to(data).text('Erro ao buscar imagem. Tente novamente mais tarde! 🐾')]
