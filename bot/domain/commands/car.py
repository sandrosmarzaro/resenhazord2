import random

import httpx
import structlog

from bot.data.car_brands import FIPE_BRANDS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.car_image_finder import CarImageFinder
from bot.infrastructure.fipe_client import FipeClient
from bot.infrastructure.wikimedia_client import WikimediaClient

logger = structlog.get_logger()


class CarCommand(Command):
    MAX_YEAR_RETRIES = 3
    MAX_VALID_YEAR = 2030
    NOT_FOUND_MESSAGE = 'Ops, não achei esse carro agora! 🚗'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='carro',
            aliases=['car'],
            flags=[Flag.SHOW, Flag.DM, 'wiki'],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba a foto de um carro aleatório com modelo, ano e preço FIPE.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            brand = random.choice(FIPE_BRANDS)
            model = random.choice(await FipeClient.models(brand.fipe_code))
            years = await FipeClient.years(brand.fipe_code, model['codigo'])

            details = await self._fetch_details(brand.fipe_code, model['codigo'], years)
            caption = self._build_caption(brand, model, details)

            thumb = await CarImageFinder.find(
                brand.name, model['nome'], wiki_only='wiki' in parsed.flags
            )
            if not thumb:
                return [Reply.to(data).text(caption)]

            buffer = await WikimediaClient.download(thumb)
            return [Reply.to(data).image_buffer(buffer, caption)]
        except httpx.HTTPError as error:
            logger.warning('upstream_failed', upstream='parallelum/wikipedia', error=str(error))
            return [Reply.to(data).text(self.NOT_FOUND_MESSAGE)]
        except Exception:
            logger.exception('upstream_failed', upstream='parallelum/wikipedia')
            return [Reply.to(data).text(self.NOT_FOUND_MESSAGE)]

    async def _fetch_details(
        self, brand_code: str, model_code: int, years: list[dict]
    ) -> dict | None:
        shuffled = years.copy()
        random.shuffle(shuffled)
        for year in shuffled[: self.MAX_YEAR_RETRIES]:
            details = await FipeClient.details(brand_code, model_code, year['codigo'])
            if 'error' not in details:
                return details
        return None

    def _build_caption(self, brand, model: dict, details: dict | None) -> str:
        if details:
            year = self._format_year(details['AnoModelo'])
            return '\n'.join(
                [
                    f'{brand.emoji} *{details["Marca"]} {details["Modelo"]}*',
                    f'📅 {year} | ⛽ {details["Combustivel"]}',
                    f'💰 {details["Valor"]}',
                    brand.origin,
                ]
            )
        return f'{brand.emoji} *{brand.name} {model["nome"]}*\n{brand.origin}'

    @classmethod
    def _format_year(cls, year: int) -> str:
        if year > cls.MAX_VALID_YEAR:
            return '0 km'
        return str(year)
