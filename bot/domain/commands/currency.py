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
    _MIN_DECIMALS: ClassVar[int] = 2
    _SIGNIFICANT_DIGITS: ClassVar[int] = 2

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

        amount_formatted = self._format_number(amount, 0 if amount.is_integer() else 2)
        lines = ['💵 Cotação em Reais 💰', '']
        for code, flag in CURRENCY_FLAGS.items():
            if code in rates:
                reais = amount * rates['BRL'] / rates[code]
                formatted = self._format_number(reais, self._decimals(reais))
                lines.append(f'{flag} {amount_formatted} {code} = R$ {formatted}')

        return [Reply.to(data).text('\n'.join(lines))]

    @classmethod
    def _decimals(cls, value: float) -> int:
        magnitude = math.floor(math.log10(value))
        return max(cls._MIN_DECIMALS, cls._SIGNIFICANT_DIGITS - 1 - magnitude)

    @staticmethod
    def _format_number(value: float, decimals: int) -> str:
        formatted = f'{value:,.{decimals}f}'
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
