import math
from typing import ClassVar

from bot.data.currency import CURRENCY_FLAGS
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


class CurrencyCommand(Command):
    API_URL = 'https://cdn.moneyconvert.net/api/latest.json'
    # More than two decimals makes Android WhatsApp link the digits after the
    # comma (issue #387), so cheap currencies are quoted per 10, 100, 1.000 units.
    _DECIMALS: ClassVar[int] = 2
    _MIN_QUOTED_REAIS: ClassVar[float] = 0.1
    _SCALE_STEP: ClassVar[int] = 10

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='moeda',
            aliases=['currency'],
            args=ArgType.OPTIONAL,
            args_label='valor',
            category=Category.INFORMATION,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Cotação de outras moedas em reais.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        amount_str = parsed.rest.strip()
        try:
            amount = float(amount_str.replace(',', '.')) if amount_str else 1.0
        except ValueError:
            amount = math.nan
        if not (math.isfinite(amount) and amount > 0):
            return [Reply.to(data).text('Valor inválido! Manda um número positivo 🙂')]

        response = await HttpClient.get(self.API_URL)
        response.raise_for_status()
        rates = response.json()['rates']

        lines = ['💵 Cotação em Reais 💰', '']
        for code, flag in CURRENCY_FLAGS.items():
            if code in rates:
                lines.append(f'{flag} {self._quote(amount, rates["BRL"] / rates[code], code)}')

        return [Reply.to(data).text('\n'.join(lines))]

    @classmethod
    def _quote(cls, amount: float, reais_per_unit: float, code: str) -> str:
        while amount * reais_per_unit < cls._MIN_QUOTED_REAIS:
            amount *= cls._SCALE_STEP
        amount_decimals = 0 if round(amount, cls._DECIMALS).is_integer() else cls._DECIMALS
        amount_formatted = cls._format_number(amount, amount_decimals)
        reais_formatted = cls._format_number(amount * reais_per_unit, cls._DECIMALS)
        return f'{amount_formatted} {code} = R$ {reais_formatted}'

    @staticmethod
    def _format_number(value: float, decimals: int) -> str:
        formatted = f'{value:,.{decimals}f}'
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
