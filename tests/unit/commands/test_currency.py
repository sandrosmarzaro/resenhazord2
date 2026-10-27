import httpx
import pytest

from bot.domain.commands.currency import CurrencyCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory

MOCK_RATES = {
    'base': 'USD',
    'rates': {
        'BRL': 5.00757101,
        'USD': 1.0,
        'EUR': 0.85328081,
        'GBP': 0.74332118,
        'CHF': 0.78983461,
        'JPY': 159.20498966,
        'CNY': 6.82420801,
        'HKD': 7.83041706,
        'CAD': 1.38494536,
        'AUD': 1.41515044,
        'INR': 92.99713403,
        'AOA': 917.97603855,
        'ARS': 1370.48686575,
    },
}


@pytest.fixture
def command():
    return CurrencyCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',moeda 100', True),
            (',moeda 50.00', True),
            (',moeda 1000', True),
            (',currency 100', True),
            (', MOEDA 50', True),
            (',moeda', True),
            ('moeda 100', False),
            (',dinheiro 100', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


API_URL = 'https://cdn.moneyconvert.net/api/latest.json'


@pytest.fixture
def rates(respx_mock):
    return respx_mock.get(API_URL).mock(return_value=httpx.Response(200, json=MOCK_RATES))


async def _reply(command, text: str) -> str:
    messages = await command.run(GroupCommandDataFactory.build(text=text))
    assert isinstance(messages[0].content, TextContent)
    return messages[0].content.text


class TestExecute:
    @pytest.mark.anyio
    async def test_prices_one_unit_of_each_currency_in_reais(self, command, rates):
        text = await _reply(command, ',moeda')

        assert '🇺🇸 1 USD = R$ 5,01' in text
        assert '🇪🇺 1 EUR = R$ 5,87' in text

    @pytest.mark.anyio
    async def test_small_rates_keep_two_significant_digits(self, command, rates):
        text = await _reply(command, ',moeda')

        assert '🇯🇵 1 JPY = R$ 0,031' in text
        assert '🇦🇷 1 ARS = R$ 0,0037' in text

    @pytest.mark.anyio
    async def test_prices_the_given_amount(self, command, rates):
        text = await _reply(command, ',moeda 100')

        assert '🇯🇵 100 JPY = R$ 3,15' in text

    @pytest.mark.anyio
    async def test_handles_decimal_comma_input(self, command, rates):
        text = await _reply(command, ',moeda 2,5')

        assert '🇺🇸 2,50 USD = R$ 12,52' in text

    @pytest.mark.anyio
    async def test_lists_every_currency(self, command, rates):
        text = await _reply(command, ',currency')

        currency_lines = [line for line in text.splitlines() if ' = R$ ' in line]
        assert len(currency_lines) == len(MOCK_RATES['rates']) - 1

    @pytest.mark.anyio
    @pytest.mark.parametrize('amount', ['abc', '0', '-5', 'inf', 'nan'])
    async def test_rejects_non_positive_or_invalid_amount(self, command, amount):
        text = await _reply(command, f',moeda {amount}')

        assert text == 'Valor inválido! Manda um número positivo 🙂'

    @pytest.mark.anyio
    async def test_raises_on_api_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',moeda 100')
        respx_mock.get(API_URL).mock(return_value=httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await command.run(data)
