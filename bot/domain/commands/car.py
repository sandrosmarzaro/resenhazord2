import random

import structlog

from bot.data.car_brands import FIPE_BRANDS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.car_image_finder import CarImageFinder
from bot.infrastructure.http_client import HttpClient
from bot.infrastructure.wikimedia_client import WikimediaClient

logger = structlog.get_logger()


class CarCommand(Command):
    FIPE_BASE = 'https://parallelum.com.br/fipe/api/v1/carros/marcas'
    FIPE_TIMEOUT = 8.0
    MAX_YEAR_RETRIES = 3
    MAX_VALID_YEAR = 2030

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
            base = f'{self.FIPE_BASE}/{brand.fipe_code}'

            models_res = await HttpClient.get(f'{base}/modelos', timeout=self.FIPE_TIMEOUT)
            models_data = models_res.json()
            model = random.choice(models_data['modelos'])

            years_res = await HttpClient.get(
                f'{base}/modelos/{model["codigo"]}/anos', timeout=self.FIPE_TIMEOUT
            )
            years = years_res.json()

            details = await self._fetch_details(base, model['codigo'], years)
            caption = self._build_caption(brand, model, details)

            thumb = await CarImageFinder.find(
                brand.name, model['nome'], wiki_only='wiki' in parsed.flags
            )
            if not thumb:
                return [Reply.to(data).text(caption)]

            buffer = await WikimediaClient.download(thumb)
            return [Reply.to(data).image_buffer(buffer, caption)]
        except Exception:
            logger.exception('upstream_failed', upstream='parallelum/wikipedia')
            return [Reply.to(data).text('Ops, não achei esse carro agora! 🚗')]

    async def _fetch_details(self, base: str, model_code: int, years: list[dict]) -> dict | None:
        shuffled = years.copy()
        random.shuffle(shuffled)
        for year in shuffled[: self.MAX_YEAR_RETRIES]:
            res = await HttpClient.get(
                f'{base}/modelos/{model_code}/anos/{year["codigo"]}',
                timeout=self.FIPE_TIMEOUT,
            )
            data = res.json()
            if 'error' not in data:
                return data
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
