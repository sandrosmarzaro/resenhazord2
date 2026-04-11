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


class TestExecute:
    @pytest.mark.anyio
    async def test_converts_brl_to_all_currencies(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',moeda 100')
        respx_mock.get('https://cdn.moneyconvert.net/api/latest.json').mock(
            return_value=httpx.Response(200, json=MOCK_RATES)
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        text = messages[0].content.text
        assert 'Cotação do Real' in text
        assert '💵' in text
        assert '💰' in text
        assert 'R$ 100,00' in text
        assert 'USD:' in text
        assert 'EUR:' in text
        assert 'GBP:' in text

    @pytest.mark.anyio
    async def test_handles_decimal_comma_input(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',moeda 50,50')
        respx_mock.get('https://cdn.moneyconvert.net/api/latest.json').mock(
            return_value=httpx.Response(200, json=MOCK_RATES)
        )

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'R$ 50,50' in text

    @pytest.mark.anyio
    async def test_defaults_to_one_when_no_amount(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',moeda')
        respx_mock.get('https://cdn.moneyconvert.net/api/latest.json').mock(
            return_value=httpx.Response(200, json=MOCK_RATES)
        )

        messages = await command.run(data)

        assert len(messages) == 1
        text = messages[0].content.text
        assert 'R$ 1,00' in text
        assert 'USD:' in text

    @pytest.mark.anyio
    async def test_returns_error_for_invalid_amount(self, command):
        data = GroupCommandDataFactory.build(text=',moeda abc')

        messages = await command.run(data)

        assert 'Valor inválido' in messages[0].content.text
        assert '🤷‍♂️' in messages[0].content.text

    @pytest.mark.anyio
    async def test_shows_all_12_currencies(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',moeda 100')
        respx_mock.get('https://cdn.moneyconvert.net/api/latest.json').mock(
            return_value=httpx.Response(200, json=MOCK_RATES)
        )

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'USD:' in text
        assert 'EUR:' in text
        assert 'GBP:' in text
        assert 'CHF:' in text
        assert 'JPY:' in text
        assert 'CNY:' in text
        assert 'HKD:' in text
        assert 'CAD:' in text
        assert 'AUD:' in text
        assert 'INR:' in text
        assert 'AOA:' in text
        assert 'ARS:' in text

    @pytest.mark.anyio
    async def test_english_alias_works(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',currency 200')
        respx_mock.get('https://cdn.moneyconvert.net/api/latest.json').mock(
            return_value=httpx.Response(200, json=MOCK_RATES)
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'R$ 200,00' in messages[0].content.text

    @pytest.mark.anyio
    async def test_raises_on_api_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',moeda 100')
        respx_mock.get('https://cdn.moneyconvert.net/api/latest.json').mock(
            return_value=httpx.Response(500)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await command.run(data)
