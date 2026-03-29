import httpx
import pytest

from bot.domain.commands.country_flag import CountryFlagCommand
from bot.domain.models.message import ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return CountryFlagCommand()


@pytest.fixture(autouse=True)
def mock_translator(mocker):
    mocker.patch(
        'bot.domain.commands.country_flag.Translator.to_pt',
        side_effect=lambda text: text,
    )


def _mock_country(**overrides):
    return {
        'name': {'common': 'Brazil', 'official': 'Federative Republic of Brazil'},
        'flags': {'png': 'https://flagcdn.com/w320/br.png'},
        'cca3': 'BRA',
        'capital': ['Brasília'],
        'region': 'Americas',
        'subregion': 'South America',
        'population': 212559417,
        'area': 8515767,
        'languages': {'por': 'Portuguese'},
        'currencies': {'BRL': {'name': 'Brazilian real', 'symbol': 'R$'}},
        **overrides,
    }


def _mock_detail():
    return {
        'timezones': ['UTC-03:00'],
        'latlng': [-15.79, -47.88],
        'idd': {'root': '+5', 'suffixes': ['5']},
        'borders': ['ARG', 'BOL', 'COL'],
        'car': {'side': 'right'},
    }


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
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            return_value=httpx.Response(200, json=[_mock_country()])
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://flagcdn.com/w320/br.png'
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
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            return_value=httpx.Response(200, json=[_mock_country()])
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Federative Republic of Brazil' in caption

    @pytest.mark.anyio
    async def test_omits_official_name_when_same(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        country = _mock_country(name={'common': 'Japan', 'official': 'Japan'})
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            return_value=httpx.Response(200, json=[country])
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert caption.count('Japan') == 1

    @pytest.mark.anyio
    async def test_handles_missing_subregion(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        country = _mock_country(subregion=None, region='Antarctic')
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            return_value=httpx.Response(200, json=[country])
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Antártida' in caption

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira')
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            side_effect=Exception('API down')
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text


class TestDetailFlag:
    @pytest.mark.anyio
    async def test_detail_flag_adds_extra_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira detail')
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            return_value=httpx.Response(200, json=[_mock_country()])
        )
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/alpha/BRA').mock(
            return_value=httpx.Response(200, json=_mock_detail())
        )
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
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            return_value=httpx.Response(200, json=[_mock_country()])
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'UTC-03:00' not in caption
        assert 'Fronteiras' not in caption

    @pytest.mark.anyio
    async def test_detail_handles_missing_fields(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bandeira detail')
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/all').mock(
            return_value=httpx.Response(200, json=[_mock_country()])
        )
        respx_mock.get(url__startswith='https://restcountries.com/v3.1/alpha/BRA').mock(
            return_value=httpx.Response(
                200, json={'timezones': [], 'latlng': [], 'idd': {}, 'borders': [], 'car': {}}
            )
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Brazil' in caption
        assert 'Fronteiras' not in caption
        assert 'Mão' not in caption
