import httpx
import pytest

from bot.data.car_brands import FIPE_BRANDS
from bot.domain.commands.car import CarCommand
from bot.domain.models.message import ImageBufferContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

MOCK_MODELS = {
    'modelos': [
        {'codigo': 1001, 'nome': 'Golf 1.6'},
        {'codigo': 1002, 'nome': 'Polo 1.0'},
    ],
}

MOCK_YEARS = [
    {'codigo': '2020-1', 'nome': '2020 Gasolina'},
    {'codigo': '2019-1', 'nome': '2019 Gasolina'},
]

MOCK_DETAILS = {
    'Marca': 'Volkswagen',
    'Modelo': 'Golf 1.6',
    'AnoModelo': 2020,
    'Combustivel': 'Gasolina',
    'Valor': 'R$ 80.000,00',
    'CodigoFipe': '005215-9',
}

MOCK_WIKI_RESPONSE = {
    'query': {
        'pages': {
            '12345': {
                'title': 'Volkswagen Golf',
                'thumbnail': {'source': 'https://upload.wikimedia.org/thumb/a/a1/640px-Golf.jpg'},
            },
        },
    },
}


@pytest.fixture
def command():
    return CarCommand()


@pytest.fixture
def fipe_routes(respx_mock):
    respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
        return_value=httpx.Response(200, json=MOCK_MODELS)
    )
    respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
        return_value=httpx.Response(200, json=MOCK_YEARS)
    )
    respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
        return_value=httpx.Response(200, json=MOCK_DETAILS)
    )
    respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
        return_value=httpx.Response(200, json=MOCK_WIKI_RESPONSE)
    )
    respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
        return_value=httpx.Response(200, content=b'fake-image')
    )
    return respx_mock


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',carro', True),
            (', carro', True),
            (', CARRO', True),
            (', carro show', True),
            (', carro dm', True),
            (', carro wiki', True),
            (', carro wiki show', True),
            (', carro show wiki', True),
            ('carro', False),
            (',carrof', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestFipeApiCalls:
    @pytest.mark.anyio
    async def test_returns_image_with_caption(self, command, fipe_routes):
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_caption_contains_brand_model_year_price(self, command, fipe_routes):
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Volkswagen' in caption
        assert 'Golf 1.6' in caption
        assert '2020' in caption
        assert 'R$ 80.000,00' in caption
        assert 'Gasolina' in caption


class TestWikipedia:
    @pytest.mark.anyio
    async def test_text_only_when_no_thumbnail(self, command, respx_mock):
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=MOCK_DETAILS)
        )
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={'query': {'pages': {'1': {}}}})
        )
        respx_mock.get(url__startswith='https://commons.wikimedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'Volkswagen' in messages[0].content.text

    @pytest.mark.anyio
    async def test_text_only_when_wiki_query_absent(self, command, respx_mock):
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=MOCK_DETAILS)
        )
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        respx_mock.get(url__startswith='https://commons.wikimedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'Golf' in messages[0].content.text

    @pytest.mark.anyio
    async def test_brand_only_article_uses_brand_logo(self, command, respx_mock, mocker):
        mocker.patch(
            'bot.domain.commands.car.random.choice',
            side_effect=[
                next(b for b in FIPE_BRANDS if b.name == 'Acura'),
                MOCK_MODELS['modelos'][0],
            ],
        )

        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=MOCK_DETAILS)
        )
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(
                200,
                json={
                    'query': {
                        'pages': {
                            '1': {
                                'title': 'Acura',
                                'thumbnail': {'source': 'https://upload.wikimedia.org/logo.png'},
                            }
                        }
                    }
                },
            )
        )
        respx_mock.get(url__startswith='https://commons.wikimedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
            return_value=httpx.Response(200, content=b'fake-logo')
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_falls_back_to_commons_when_no_wiki_thumb(self, command, respx_mock):
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=MOCK_DETAILS)
        )
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={'query': {'pages': {'1': {}}}})
        )
        respx_mock.get(url__startswith='https://commons.wikimedia.org/w/api.php').mock(
            return_value=httpx.Response(
                200,
                json={
                    'query': {
                        'pages': {
                            '99': {
                                'thumbnail': {
                                    'source': 'https://upload.wikimedia.org/thumb/x/xx/640px-Golf.jpg'
                                }
                            }
                        }
                    }
                },
            )
        )
        respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)


class TestBrandDetection:
    @pytest.mark.parametrize(
        ('brand_name', 'page_title', 'expected'),
        [
            ('Jeep', 'Pontiac', True),
            ('Jeep', 'Pontiac Motors', True),
            ('Volkswagen', 'Volkswagen', True),
            ('Audi', 'Audi Automobiles', True),
            ('Ford', 'Ford Motor', True),
            ('Jeep', 'Jeep Grand Cherokee', False),
            ('Toyota', 'Toyota Corolla', False),
            ('BMW', '', False),
        ],
    )
    def test_is_brand_only_page(self, command, brand_name, page_title, expected):
        assert command._is_brand_only_page(brand_name, page_title) is expected

    @pytest.mark.anyio
    async def test_cross_brand_page_rejected_uses_brand_logo(self, command, respx_mock, mocker):
        mocker.patch(
            'bot.domain.commands.car.random.choice',
            side_effect=[
                next(b for b in FIPE_BRANDS if b.name == 'Jeep'),
                MOCK_MODELS['modelos'][0],
            ],
        )
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=MOCK_DETAILS)
        )
        wiki_call_count = 0

        def wiki_handler(request):
            nonlocal wiki_call_count
            wiki_call_count += 1
            if wiki_call_count == 1:
                return httpx.Response(
                    200,
                    json={
                        'query': {
                            'pages': {
                                '1': {
                                    'title': 'Pontiac',
                                    'thumbnail': {
                                        'source': 'https://upload.wikimedia.org/pontiac.png'
                                    },
                                }
                            }
                        }
                    },
                )
            return httpx.Response(
                200,
                json={
                    'query': {
                        'pages': {
                            '2': {
                                'title': 'Jeep',
                                'thumbnail': {
                                    'source': 'https://upload.wikimedia.org/jeep-logo.png'
                                },
                            }
                        }
                    }
                },
            )

        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            side_effect=wiki_handler
        )
        respx_mock.get(url__startswith='https://commons.wikimedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
            return_value=httpx.Response(200, content=b'fake-jeep-logo')
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)
        assert wiki_call_count == 2


class TestBrandLogoFallback:
    @pytest.mark.anyio
    async def test_text_only_when_brand_logo_also_fails(self, command, respx_mock):
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=MOCK_DETAILS)
        )
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        respx_mock.get(url__startswith='https://commons.wikimedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)


class TestYearRetryLogic:
    @pytest.mark.anyio
    async def test_retries_next_year_on_fipe_error(self, command, respx_mock):
        call_count = 0

        def detail_handler(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json={'error': 'Dado não encontrado'})
            return httpx.Response(200, json=MOCK_DETAILS)

        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(side_effect=detail_handler)
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json=MOCK_WIKI_RESPONSE)
        )
        respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert call_count == 2
        caption = messages[0].content.caption
        assert 'Golf 1.6' in caption

    @pytest.mark.anyio
    async def test_fallback_caption_when_all_years_fail(self, command, respx_mock, mocker):
        mocker.patch(
            'bot.domain.commands.car.random.choice',
            side_effect=[FIPE_BRANDS[0], MOCK_MODELS['modelos'][0]],
        )
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json={'error': 'Dado não encontrado'})
        )
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={'query': {'pages': {'1': {}}}})
        )
        respx_mock.get(url__startswith='https://commons.wikimedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={})
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'Golf' in messages[0].content.text


class TestWikiFlag:
    @pytest.mark.anyio
    async def test_wiki_flag_skips_commons_fallback(self, command, respx_mock):
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=MOCK_DETAILS)
        )
        wiki_route = respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json={'query': {'pages': {'1': {}}}})
        )
        commons_route = respx_mock.get(
            url__startswith='https://commons.wikimedia.org/w/api.php'
        ).mock(return_value=httpx.Response(200, json={}))
        data = GroupCommandDataFactory.build(text=',carro wiki')
        messages = await command.run(data)

        assert wiki_route.call_count == 2
        assert commons_route.call_count == 0
        assert isinstance(messages[0].content, TextContent)


class TestFlags:
    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command, fipe_routes):
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, fipe_routes):
        data = GroupCommandDataFactory.build(text=',carro show')
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_dm_flag_redirects_jid(self, command, fipe_routes):
        data = GroupCommandDataFactory.build(text=',carro dm')
        messages = await command.run(data)

        assert messages[0].jid == data.participant

    @pytest.mark.anyio
    async def test_dm_flag_in_private_keeps_jid(self, command, fipe_routes):
        data = PrivateCommandDataFactory.build(text=',carro dm')
        messages = await command.run(data)

        assert messages[0].jid == data.jid


class TestErrorHandling:
    @pytest.mark.anyio
    async def test_returns_error_text_on_failure(self, command, respx_mock):
        respx_mock.get(url__regex=r'.*/fipe/.*').mock(side_effect=Exception('Network error'))
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro ao buscar carro' in messages[0].content.text


class TestYearFormatting:
    @pytest.mark.parametrize(
        ('year', 'expected'),
        [
            (2020, '2020'),
            (1990, '1990'),
            (2030, '2030'),
            (32000, '0 km'),
            (99999, '0 km'),
        ],
    )
    def test_format_year(self, year, expected):
        assert CarCommand._format_year(year) == expected

    @pytest.mark.anyio
    async def test_caption_shows_zero_km_for_fipe_32000(self, command, respx_mock):
        details_32000 = {**MOCK_DETAILS, 'AnoModelo': 32000}
        respx_mock.get(url__regex=r'.*/fipe/api/v1/carros/marcas/\d+/modelos$').mock(
            return_value=httpx.Response(200, json=MOCK_MODELS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos$').mock(
            return_value=httpx.Response(200, json=MOCK_YEARS)
        )
        respx_mock.get(url__regex=r'.*/modelos/\d+/anos/[^/]+$').mock(
            return_value=httpx.Response(200, json=details_32000)
        )
        respx_mock.get(url__startswith='https://en.wikipedia.org/w/api.php').mock(
            return_value=httpx.Response(200, json=MOCK_WIKI_RESPONSE)
        )
        respx_mock.get(url__startswith='https://upload.wikimedia.org/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        data = GroupCommandDataFactory.build(text=',carro')
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '0 km' in caption
        assert '32000' not in caption


class TestModelNameParsing:
    @pytest.mark.parametrize(
        ('nome', 'expected'),
        [
            ('Golf 1.6', 'Golf'),
            ('911 Targa 4S 3.0 420cv (991)', '911 Targa 4S'),
            ('Tiggo 5X SPORT 1.5 Turbo', 'Tiggo 5X SPORT'),
            ('Polo', 'Polo'),
        ],
    )
    def test_base_model_name(self, nome, expected):
        assert CarCommand._base_model_name(nome) == expected

    @pytest.mark.parametrize(
        ('nome', 'expected'),
        [
            ('Civic Sedan LX/LXL 1.7 16V', 'Civic'),
            ('Palio Weekend Adv. Ext.', 'Palio Weekend'),
            ('Golf 1.6', 'Golf'),
            ('Polo', 'Polo'),
        ],
    )
    def test_wiki_model_name(self, nome, expected):
        assert CarCommand._wiki_model_name(nome) == expected
