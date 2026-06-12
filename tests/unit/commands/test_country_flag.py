import httpx
import pytest

from bot.domain.commands.country_flag import CountryFlagCommand
from bot.domain.models.message import ImageContent, TextContent
from bot.infrastructure.restcountries_client import RestCountriesClient
from tests.factories.command_data import GroupCommandDataFactory

V5_LIST_URL = 'https://api.restcountries.com/countries/v5'


@pytest.fixture
def command():
    return CountryFlagCommand(api_key='rc_live_test')


@pytest.fixture(autouse=True)
def reset_cache():
    RestCountriesClient.reset_cache()
    yield
    RestCountriesClient.reset_cache()


@pytest.fixture(autouse=True)
def mock_translator(mocker):
    mocker.patch(
        'bot.domain.commands.country_flag.Translator.to_pt',
        side_effect=lambda text: text,
    )


def _mock_country(**overrides):
    return {
        'names': {'common': 'Brazil', 'official': 'Federative Republic of Brazil'},
        'flag': {'url_png': 'https://flags.restcountries.com/v5/w160/br.png', 'emoji': '🇧🇷'},
        'capitals': [{'name': 'Brasília'}],
        'region': 'Americas',
        'subregion': 'South America',
        'population': 212559417,
        'area': {'kilometers': 8515767},
        'languages': [{'name': 'Portuguese'}],
        'currencies': [{'code': 'BRL', 'name': 'Brazilian real', 'symbol': 'R$'}],
        'timezones': ['UTC-03:00'],
        'coordinates': {'lat': -15.79, 'lng': -47.88},
        'calling_codes': ['55'],
        'borders': ['ARG', 'BOL', 'COL'],
        'cars': {'driving_side': 'right'},
        **overrides,
    }


def _v5_response(*countries):
    return httpx.Response(
        200, json={'data': {'objects': list(countries), 'meta': {'total': len(countries)}}}
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', bandeira', True),
            (',bandeira', True),
            (', BANDEIRA', True),
            (', bandeira show', True),
            (', bandeira detail', True),
            (', bandeira dm', True),
            ('  , bandeira  ', True),
            ('bandeira', False),
            ('hello', False),
            (', bandeira extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_image_with_country_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        respx_mock.get(url__startswith=V5_LIST_URL).mock(return_value=_v5_response(_mock_country()))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://flags.restcountries.com/v5/w160/br.png'
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Brazil' in caption
        assert 'Brasília' in caption
        assert 'América do Sul' in caption
        assert 'Portuguese' in caption
        assert 'Brazilian real' in caption

    @pytest.mark.anyio
    async def test_includes_official_name_when_different(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        respx_mock.get(url__startswith=V5_LIST_URL).mock(return_value=_v5_response(_mock_country()))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Federative Republic of Brazil' in caption

    @pytest.mark.anyio
    async def test_omits_official_name_when_same(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        country = _mock_country(names={'common': 'Japan', 'official': 'Japan'})
        respx_mock.get(url__startswith=V5_LIST_URL).mock(return_value=_v5_response(country))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert caption.count('Japan') == 1

    @pytest.mark.anyio
    async def test_handles_missing_subregion(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        country = _mock_country(subregion=None, region='Antarctic')
        respx_mock.get(url__startswith=V5_LIST_URL).mock(return_value=_v5_response(country))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Antártida' in caption

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        respx_mock.get(url__startswith=V5_LIST_URL).mock(side_effect=Exception('API down'))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text

    @pytest.mark.anyio
    async def test_skips_countries_without_flag(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        no_flag = _mock_country(
            names={'common': 'Abkhazia', 'official': 'Abkhazia'},
            flag={'url_png': '', 'emoji': ''},
        )
        respx_mock.get(url__startswith=V5_LIST_URL).mock(
            return_value=_v5_response(no_flag, _mock_country())
        )

        messages = await command.run(data)

        assert messages[0].content.url == 'https://flags.restcountries.com/v5/w160/br.png'

    @pytest.mark.anyio
    async def test_returns_error_on_deprecated_200_body(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        respx_mock.get(url__startswith=V5_LIST_URL).mock(
            return_value=httpx.Response(
                200, json={'success': False, 'data': None, 'errors': [{'message': 'deprecated'}]}
            )
        )

        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text


class TestDetailFlag:
    @pytest.mark.anyio
    async def test_detail_flag_adds_extra_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira detail')
        respx_mock.get(url__startswith=V5_LIST_URL).mock(return_value=_v5_response(_mock_country()))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'UTC-03:00' in caption
        assert '-15.79' in caption
        assert '+55' in caption
        assert 'ARG' in caption
        assert 'Direita' in caption

    @pytest.mark.anyio
    async def test_without_detail_flag_omits_extra_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        respx_mock.get(url__startswith=V5_LIST_URL).mock(return_value=_v5_response(_mock_country()))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'UTC-03:00' not in caption
        assert '🗺️' not in caption

    @pytest.mark.anyio
    async def test_detail_handles_missing_fields(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira detail')
        country = _mock_country(timezones=[], coordinates={}, calling_codes=[], borders=[], cars={})
        respx_mock.get(url__startswith=V5_LIST_URL).mock(return_value=_v5_response(country))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Brazil' in caption
        assert '🗺️' not in caption
        assert '🚗' not in caption
