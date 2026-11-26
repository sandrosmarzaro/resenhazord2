import math
from typing import ClassVar

from bot.data.currency import ASSET_GROUPS, AssetGroup
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
from bot.domain.services.asset_prices import AssetPrices


class CurrencyCommand(Command):
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
        return 'Cotação de moedas, cripto, metais e Robux em reais.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        amount_str = parsed.rest.strip()
        try:
            amount = float(amount_str.replace(',', '.')) if amount_str else 1.0
        except ValueError:
            amount = math.nan
        if not (math.isfinite(amount) and amount > 0):
            return [Reply.to(data).text('Valor inválido! Manda um número positivo 🙂')]

        prices = await AssetPrices.in_reais()
        sections = ['💵 Cotação em Reais 💰']
        sections.extend(self._section(group, amount, prices) for group in ASSET_GROUPS)
        return [Reply.to(data).text('\n\n'.join(sections))]

    @classmethod
    def _section(cls, group: AssetGroup, amount: float, prices: dict[str, float]) -> str:
        return '\n'.join(
            f'{icon} {cls._quote(amount, prices[code], group.unit + code)}{group.note}'
            for code, icon in group.icons.items()
            if code in prices
        )

    @classmethod
    def _quote(cls, amount: float, reais_per_unit: float, label: str) -> str:
        while amount * reais_per_unit < cls._MIN_QUOTED_REAIS:
            amount *= cls._SCALE_STEP
        amount_decimals = 0 if round(amount, cls._DECIMALS).is_integer() else cls._DECIMALS
        amount_formatted = cls._format_number(amount, amount_decimals)
        reais_formatted = cls._format_number(amount * reais_per_unit, cls._DECIMALS)
        return f'{amount_formatted} {label} = R$ {reais_formatted}'

    @staticmethod
    def _format_number(value: float, decimals: int) -> str:
        formatted = f'{value:,.{decimals}f}'
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
