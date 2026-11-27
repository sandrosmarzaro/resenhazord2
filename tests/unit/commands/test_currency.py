import re

import httpx
import pytest
from structlog.testing import capture_logs

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
        'BTC': 1.653e-05,
        'ETH': 0.00059092,
        'DOGE': 17.58767456,
        'XAU': 0.00028042,
        'XAG': 0.02408588,
        'XPT': 0.00077258,
    },
}
MOCK_COINGECKO = {'solana': {'brl': 408.87}}
FIAT_COUNT = 12
CRYPTO_COUNT = 4
METAL_COUNT = 3


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
COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'


@pytest.fixture
def coingecko(respx_mock):
    return respx_mock.get(COINGECKO_URL, params={'ids': 'solana', 'vs_currencies': 'brl'}).mock(
        return_value=httpx.Response(200, json=MOCK_COINGECKO)
    )


@pytest.fixture
def rates(respx_mock, coingecko):
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
    async def test_scales_cheap_currencies_up_until_they_cost_ten_cents(self, command, rates):
        text = await _reply(command, ',moeda')

        assert '🇯🇵 10 JPY = R$ 0,31' in text
        assert '🇦🇷 100 ARS = R$ 0,37' in text

    @pytest.mark.anyio
    async def test_never_shows_more_than_two_decimals(self, command, rates):
        text = await _reply(command, ',moeda')

        prices = re.findall(r'R\$ (\S+)', text)
        assert all(re.fullmatch(r'[\d.]+,\d{2}', price) for price in prices)

    @pytest.mark.anyio
    async def test_scales_a_fractional_amount_only_where_it_costs_under_ten_cents(
        self, command, rates
    ):
        text = await _reply(command, ',moeda 0,07')

        assert '🇺🇸 0,07 USD = R$ 0,35' in text
        assert '🇯🇵 7 JPY = R$ 0,22' in text

    @pytest.mark.anyio
    async def test_prices_the_given_amount(self, command, rates):
        text = await _reply(command, ',moeda 100')

        assert '🇯🇵 100 JPY = R$ 3,15' in text

    @pytest.mark.anyio
    async def test_handles_decimal_comma_input(self, command, rates):
        text = await _reply(command, ',moeda 2,5')

        assert '🇺🇸 2,50 USD = R$ 12,52' in text

    @pytest.mark.anyio
    async def test_lists_every_asset(self, command, rates):
        text = await _reply(command, ',currency')

        asset_lines = [line for line in text.splitlines() if ' = R$ ' in line]
        assert len(asset_lines) == FIAT_COUNT + CRYPTO_COUNT + METAL_COUNT + 1

    @pytest.mark.anyio
    @pytest.mark.parametrize('amount', ['0', '-5', 'inf', 'nan', '0 dólar', 'euro -1'])
    async def test_rejects_non_positive_or_invalid_amount(self, command, amount):
        text = await _reply(command, f',moeda {amount}')

        assert text == 'Valor inválido! Manda um número positivo 🙂'

    @pytest.mark.anyio
    async def test_raises_on_api_failure(self, command, respx_mock, coingecko):
        data = GroupCommandDataFactory.build(text=',moeda 100')
        respx_mock.get(API_URL).mock(return_value=httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await command.run(data)


class TestAssets:
    @pytest.mark.anyio
    async def test_quotes_crypto_from_the_rates(self, command, rates):
        text = await _reply(command, ',moeda')

        assert '₿ 1 BTC = R$ 302.938,36' in text
        assert 'Ξ 1 ETH = R$ 8.474,19' in text
        assert '🐕 1 DOGE = R$ 0,28' in text

    @pytest.mark.anyio
    async def test_quotes_solana_from_coingecko(self, command, rates):
        text = await _reply(command, ',moeda')

        assert '◎ 1 SOL = R$ 408,87' in text

    @pytest.mark.anyio
    async def test_quotes_metals_per_troy_ounce(self, command, rates):
        text = await _reply(command, ',moeda')

        assert '🥇 1 oz XAU = R$ 17.857,40' in text
        assert '🥈 1 oz XAG = R$ 207,90' in text
        assert '⚪ 1 oz XPT = R$ 6.481,62' in text

    @pytest.mark.anyio
    async def test_quotes_robux_at_the_store_price(self, command, rates):
        text = await _reply(command, ',moeda')

        assert '🎮 10 Robux = R$ 0,50 (preço da loja)' in text

    @pytest.mark.anyio
    async def test_multiplies_asset_rows_by_the_amount(self, command, rates):
        text = await _reply(command, ',moeda 0,5')

        assert '₿ 0,50 BTC = R$ 151.469,18' in text
        assert '🥇 0,50 oz XAU = R$ 8.928,70' in text

    @pytest.mark.anyio
    async def test_splits_the_reply_into_fiat_crypto_metals_and_robux(self, command, rates):
        text = await _reply(command, ',moeda')

        sections = text.split('\n\n')[1:]
        assert [len(section.splitlines()) for section in sections] == [
            FIAT_COUNT,
            CRYPTO_COUNT,
            METAL_COUNT,
            1,
        ]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'response',
        [httpx.Response(429), httpx.Response(200, json={})],
        ids=['rate_limited', 'missing_coin'],
    )
    async def test_drops_solana_when_coingecko_fails(self, command, rates, coingecko, response):
        coingecko.mock(return_value=response)

        with capture_logs() as logs:
            text = await _reply(command, ',moeda')

        assert 'SOL' not in text
        assert [log['upstream'] for log in logs if log['event'] == 'upstream_failed'] == [
            'coingecko'
        ]


def _quote_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if ' = R$ ' in line]


class TestFilter:
    @pytest.mark.anyio
    @pytest.mark.parametrize('name', ['dólar', 'dolar', 'DÓLAR', 'usd', 'USD'])
    async def test_quotes_only_the_named_asset(self, command, rates, name):
        text = await _reply(command, f',moeda {name}')

        assert _quote_lines(text) == ['🇺🇸 1 USD = R$ 5,01']

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('name', 'line'),
        [
            ('dólar canadense', '🇨🇦 1 CAD = R$ 3,62'),
            ('bitcoin', '₿ 1 BTC = R$ 302.938,36'),
            ('solana', '◎ 1 SOL = R$ 408,87'),
            ('ouro', '🥇 1 oz XAU = R$ 17.857,40'),
            ('robux', '🎮 10 Robux = R$ 0,50 (preço da loja)'),
        ],
    )
    async def test_answers_to_pt_br_names(self, command, rates, name, line):
        text = await _reply(command, f',moeda {name}')

        assert _quote_lines(text) == [line]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('name', 'count'),
        [
            ('moedas', FIAT_COUNT),
            ('fiat', FIAT_COUNT),
            ('cripto', CRYPTO_COUNT),
            ('crypto', CRYPTO_COUNT),
            ('metais', METAL_COUNT),
            ('metal', METAL_COUNT),
        ],
    )
    async def test_quotes_a_whole_group(self, command, rates, name, count):
        text = await _reply(command, f',moeda {name}')

        assert len(_quote_lines(text)) == count

    @pytest.mark.anyio
    @pytest.mark.parametrize('text', [',moeda 10 euro', ',moeda euro 10', ',moeda euro 10,0'])
    async def test_takes_the_amount_on_either_side(self, command, rates, text):
        reply = await _reply(command, text)

        assert _quote_lines(reply) == ['🇪🇺 10 EUR = R$ 58,69']

    @pytest.mark.anyio
    @pytest.mark.parametrize('name', ['abc', 'dólar falso', 'peseta 10'])
    async def test_lists_the_groups_for_an_unknown_name_without_calling_the_api(
        self, command, rates, name
    ):
        text = await _reply(command, f',moeda {name}')

        assert 'moedas, cripto, metais ou robux' in text
        assert not rates.called
