import math
from typing import ClassVar

from bot.data.currency import AssetGroup
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
from bot.domain.services.asset_filter import AssetFilter
from bot.domain.services.asset_prices import AssetPrices


class CurrencyCommand(Command):
    # More than two decimals makes Android WhatsApp link the digits after the
    # comma (issue #387), so cheap currencies are quoted per 10, 100, 1.000 units.
    _DECIMALS: ClassVar[int] = 2
    _MIN_QUOTED_REAIS: ClassVar[float] = 0.1
    _SCALE_STEP: ClassVar[int] = 10
    _DEFAULT_AMOUNT: ClassVar[float] = 1.0
    _AMOUNT_POSITIONS: ClassVar[tuple[int, ...]] = (0, -1)
    _UNKNOWN_ASSET: ClassVar[str] = (
        'Não conheço essa moeda! 🤷‍♂️\n\n'
        'Tenta um grupo (moedas, cripto, metais ou robux) ou um nome, tipo dólar, bitcoin ou ouro.'
    )

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='moeda',
            aliases=['currency'],
            args=ArgType.OPTIONAL,
            args_label='valor moeda',
            category=Category.INFORMATION,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Cotação de moedas, cripto, metais e Robux em reais.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        amount, name = self._split_amount(parsed.rest)
        if not (math.isfinite(amount) and amount > 0):
            return [Reply.to(data).text('Valor inválido! Manda um número positivo 🙂')]
        groups = AssetFilter.groups(name)
        if groups is None:
            return [Reply.to(data).text(self._UNKNOWN_ASSET)]

        prices = await AssetPrices.in_reais()
        sections = ['💵 Cotação em Reais 💰']
        sections.extend(self._section(group, amount, prices) for group in groups)
        return [Reply.to(data).text('\n\n'.join(sections))]

    @classmethod
    def _split_amount(cls, text: str) -> tuple[float, str]:
        words = text.split()
        for position in cls._AMOUNT_POSITIONS:
            amount = cls._number(words[position]) if words else None
            if amount is not None:
                words.pop(position)
                return amount, ' '.join(words)
        return cls._DEFAULT_AMOUNT, ' '.join(words)

    @staticmethod
    def _number(word: str) -> float | None:
        try:
            return float(word.replace(',', '.'))
        except ValueError:
            return None

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
