import random

import structlog

from bot.data.car_brands import FIPE_BRANDS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class FipeCommand(Command):
    FIPE_BASE = 'https://parallelum.com.br/fipe/api/v1/carros/marcas'
    FIPE_TIMEOUT = 8.0
    MAX_YEAR_RETRIES = 3
    MAX_VALID_YEAR = 2030

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='fipe',
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Consulte o preço FIPE de um carro aleatório.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            brand = random.choice(FIPE_BRANDS)  # noqa: S311
            base = f'{self.FIPE_BASE}/{brand.fipe_code}'

            models_res = await HttpClient.get(f'{base}/modelos', timeout=self.FIPE_TIMEOUT)
            model = random.choice(models_res.json()['modelos'])  # noqa: S311

            years_res = await HttpClient.get(
                f'{base}/modelos/{model["codigo"]}/anos', timeout=self.FIPE_TIMEOUT
            )
            details = await self._fetch_details(base, model['codigo'], years_res.json())

            if details:
                year = self._format_year(details['AnoModelo'])
                text = '\n'.join(
                    [
                        f'{brand.emoji} *{details["Marca"]} {details["Modelo"]}*',
                        f'📅 {year}   ⛽ {details["Combustivel"]}',
                        f'💰 {details["Valor"]}',
                        f'📋 FIPE: {details["CodigoFipe"]}',
                        brand.origin,
                    ]
                )
            else:
                text = f'{brand.emoji} *{brand.name} {model["nome"]}*\n{brand.origin}'

            return [Reply.to(data).text(text)]
        except Exception:
            logger.exception('fipe_command_error')
            return [Reply.to(data).text('Erro ao consultar tabela FIPE. Tente novamente! 🚗')]

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

    @classmethod
    def _format_year(cls, year: int) -> str:
        if year > cls.MAX_VALID_YEAR:
            return '0 km'
        return str(year)
