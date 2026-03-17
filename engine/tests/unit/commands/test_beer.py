from unittest.mock import patch

import pytest

from bot.domain.commands.beer import BeerCommand
from bot.domain.models.message import ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return BeerCommand()


def _mock_response(products):
    return make_json_response({'products': products})


def _beer_product(**overrides):
    return {
        'product_name': 'Heineken',
        'brands': 'Heineken',
        'image_front_url': 'https://example.com/heineken.jpg',
        'nutriments': {'alcohol_100g': 5.0},
        'quantity': '330ml',
        'origins': 'en:Netherlands',
        'countries': 'en:France,en:Brazil',
        'ingredients_text': 'Water, barley malt, hops',
        **overrides,
    }


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', cerveja', True),
            (',cerveja', True),
            (', CERVEJA', True),
            (', cerveja show', True),
            (', cerveja dm', True),
            ('  , cerveja  ', True),
            ('cerveja', False),
            ('hello', False),
            (', cerveja extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_image_with_beer_info(self, command):
        data = GroupCommandDataFactory.build(text=', cerveja')
        mock_resp = _mock_response([_beer_product()])

        with patch('bot.domain.commands.beer.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        caption = messages[0].content.caption
        assert 'Heineken' in caption
        assert '5.0%' in caption
        assert '330ml' in caption

    @pytest.mark.anyio
    async def test_strips_language_prefixes(self, command):
        data = GroupCommandDataFactory.build(text=', cerveja')
        mock_resp = _mock_response([_beer_product()])

        with patch('bot.domain.commands.beer.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Netherlands' in caption
        assert 'en:' not in caption

    @pytest.mark.anyio
    async def test_filters_products_without_name(self, command):
        data = GroupCommandDataFactory.build(text=', cerveja')
        products = [
            {'product_name': None, 'image_front_url': 'https://example.com/x.jpg'},
            _beer_product(),
        ]
        mock_resp = _mock_response(products)

        with patch('bot.domain.commands.beer.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command):
        data = GroupCommandDataFactory.build(text=', cerveja')

        with patch(
            'bot.domain.commands.beer.HttpClient.get',
            side_effect=Exception('API down'),
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text

    @pytest.mark.anyio
    async def test_handles_missing_optional_fields(self, command):
        data = GroupCommandDataFactory.build(text=', cerveja')
        product = _beer_product(
            nutriments=None,
            quantity=None,
            origins=None,
            countries=None,
            ingredients_text=None,
        )
        mock_resp = _mock_response([product])

        with patch('bot.domain.commands.beer.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
