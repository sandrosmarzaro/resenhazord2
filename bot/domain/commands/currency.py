from bot.data.currency import CURRENCIES
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
        return 'Converte valores de BRL para outras moedas.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        amount_str = parsed.rest.strip()
        amount = 1.0
        if amount_str:
            try:
                amount = float(amount_str.replace(',', '.'))
            except ValueError:
                return [Reply.to(data).text('Valor inválido! Use um número. 🤷‍♂️')]

        response = await HttpClient.get(self.API_URL)
        response.raise_for_status()
        rates = response.json()['rates']

        brl_rate = rates.get('BRL', 1)
        amount_formatted = self._format_number(amount, 2)
        lines = [
            '💵 Cotação do Real — BRL 💰',
            '',
            f'R$ {amount_formatted}',
            '',
        ]
        for code, info in CURRENCIES.items():
            if code in rates:
                rate = rates[code] / brl_rate
                converted = amount * rate
                symbol = info.symbol
                decimals = info.decimals
                formatted = self._format_number(converted, decimals)
                lines.append(f'{symbol} {code}: {formatted}')

        return [Reply.to(data).text('\n'.join(lines))]

    @staticmethod
    def _format_number(value: float, decimals: int) -> str:
        formatted = f'{value:,.{decimals}f}'
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
