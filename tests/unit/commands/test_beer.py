import httpx
import pytest

from bot.domain.commands.beer import BeerCommand
from bot.domain.models.message import ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return BeerCommand()


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
    @staticmethod
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

    @pytest.mark.anyio
    async def test_returns_image_with_beer_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cerveja')
        respx_mock.get(url__startswith='https://world.openfoodfacts.org/cgi/search.pl').mock(
            return_value=httpx.Response(200, json={'products': [self._beer_product()]})
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Heineken' in caption
        assert '5.0%' in caption
        assert '330ml' in caption

    @pytest.mark.anyio
    async def test_strips_language_prefixes(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cerveja')
        respx_mock.get(url__startswith='https://world.openfoodfacts.org/cgi/search.pl').mock(
            return_value=httpx.Response(200, json={'products': [self._beer_product()]})
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Netherlands' in caption
        assert 'en:' not in caption

    @pytest.mark.anyio
    async def test_filters_products_without_name(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cerveja')
        products = [
            {'product_name': None, 'image_front_url': 'https://example.com/x.jpg'},
            self._beer_product(),
        ]
        respx_mock.get(url__startswith='https://world.openfoodfacts.org/cgi/search.pl').mock(
            return_value=httpx.Response(200, json={'products': products})
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cerveja')
        respx_mock.get(url__startswith='https://world.openfoodfacts.org/cgi/search.pl').mock(
            side_effect=httpx.ConnectError('API down')
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Ops' in messages[0].content.text

    @pytest.mark.anyio
    async def test_handles_missing_optional_fields(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cerveja')
        product = self._beer_product(
            nutriments=None,
            quantity=None,
            origins=None,
            countries=None,
            ingredients_text=None,
        )
        respx_mock.get(url__startswith='https://world.openfoodfacts.org/cgi/search.pl').mock(
            return_value=httpx.Response(200, json={'products': [product]})
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)


class TestCatalogueDepth:
    _SEARCH_URL = 'https://world.openfoodfacts.org/cgi/search.pl'
    _PRODUCT = TestRun._beer_product()

    @pytest.fixture
    def deepest_page(self, mocker):
        mocker.patch('bot.domain.commands.beer.random.randint', side_effect=lambda _, high: high)

    @pytest.mark.anyio
    async def test_session_reaches_whole_catalogue(self, respx_mock, deepest_page):
        route = respx_mock.get(url__startswith=self._SEARCH_URL).mock(
            return_value=httpx.Response(200, json={'products': [self._PRODUCT]})
        )

        command = BeerCommand(off_session='user&abc')

        await command.run(GroupCommandDataFactory.build(text=',cerveja'))

        request = route.calls.last.request
        assert request.url.params['page'] == '600'
        assert request.headers['cookie'] == 'session=user&abc'

    @pytest.mark.anyio
    async def test_anonymous_stays_on_first_pages(self, command, respx_mock, deepest_page):
        route = respx_mock.get(url__startswith=self._SEARCH_URL).mock(
            return_value=httpx.Response(200, json={'products': [self._PRODUCT]})
        )

        await command.run(GroupCommandDataFactory.build(text=',cerveja'))

        request = route.calls.last.request
        assert (request.url.params['page'], 'cookie' in request.headers) == ('10', False)

    @pytest.mark.anyio
    async def test_rejected_session_is_logged_and_retried_on_first_pages(
        self, respx_mock, deepest_page, mocker
    ):
        logger = mocker.patch('bot.domain.commands.beer.logger')
        route = respx_mock.get(url__startswith=self._SEARCH_URL).mock(
            side_effect=[
                httpx.Response(401),
                httpx.Response(200, json={'products': [self._PRODUCT]}),
            ]
        )

        messages = await BeerCommand(off_session='expired').run(
            GroupCommandDataFactory.build(text=',cerveja')
        )

        logger.warning.assert_called_once_with('off_search_unauthorized', page=600)
        assert route.calls.last.request.url.params['page'] == '10'
        assert isinstance(messages[0].content, ImageContent)
