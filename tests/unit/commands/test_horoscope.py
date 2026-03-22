import httpx
import pytest

from bot.domain.commands.horoscope import HoroscopeCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory

MOCK_RESPONSE = {
    'data': {
        'date': '2026-03-22',
        'period': 'daily',
        'sign': 'Aries',
        'horoscope': 'Today is a great day for new beginnings.',
    },
}

MOCK_TRANSLATION = [
    [['Hoje é um ótimo dia para novos começos.', 'Today is a great day for new beginnings.']],
]


@pytest.fixture
def command():
    return HoroscopeCommand()


def _mock_horoscope_apis(respx_mock, horoscope_json=None):
    respx_mock.get('https://freehoroscopeapi.com/api/v1/get-horoscope/daily').mock(
        return_value=httpx.Response(200, json=horoscope_json or MOCK_RESPONSE)
    )
    respx_mock.get(url__startswith='https://translate.googleapis.com/translate_a/single').mock(
        return_value=httpx.Response(200, json=MOCK_TRANSLATION)
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', horóscopo áries', True),
            (',horóscopo aries', True),
            (', horoscope aries', True),
            (', HORÓSCOPO TOURO', True),
            (', horóscopo leo', True),
            (', horóscopo libra', True),
            (', horóscopo gemini', True),
            (', horóscopo peixes', True),
            (', horóscopo scorpio', True),
            (', horóscopo sagitário', True),
            (', horóscopo capricórnio', True),
            (', horóscopo', True),
            ('horóscopo', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestExecute:
    @pytest.mark.anyio
    async def test_returns_translated_horoscope(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', horóscopo áries')
        _mock_horoscope_apis(respx_mock)

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        text = messages[0].content.text
        assert '♈' in text
        assert 'Áries' in text
        assert '21/03 - 19/04' in text
        assert 'Hoje é um ótimo dia' in text

    @pytest.mark.anyio
    async def test_returns_horoscope_for_english_sign(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', horóscopo taurus')
        _mock_horoscope_apis(
            respx_mock,
            horoscope_json={'data': {**MOCK_RESPONSE['data'], 'sign': 'Taurus'}},
        )

        messages = await command.run(data)

        text = messages[0].content.text
        assert '♉' in text
        assert 'Touro' in text

    @pytest.mark.anyio
    async def test_shows_usage_when_no_sign(self, command):
        data = GroupCommandDataFactory.build(text=', horóscopo')

        messages = await command.run(data)

        assert len(messages) == 1
        text = messages[0].content.text
        assert 'Uso:' in text
        assert '♈' in text
        assert 'Áries' in text

    @pytest.mark.anyio
    async def test_shows_invalid_sign_message(self, command):
        data = GroupCommandDataFactory.build(text=', horóscopo xyz')

        messages = await command.run(data)

        assert 'Signo inválido' in messages[0].content.text

    @pytest.mark.anyio
    async def test_accent_insensitive_matching(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', horoscopo aries')
        _mock_horoscope_apis(respx_mock)

        messages = await command.run(data)

        assert 'Áries' in messages[0].content.text

    @pytest.mark.anyio
    async def test_falls_back_to_english_on_translate_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', horóscopo áries')
        respx_mock.get('https://freehoroscopeapi.com/api/v1/get-horoscope/daily').mock(
            return_value=httpx.Response(200, json=MOCK_RESPONSE)
        )
        respx_mock.get(url__startswith='https://translate.googleapis.com/translate_a/single').mock(
            return_value=httpx.Response(200, json=[])
        )

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Today is a great day' in text

    @pytest.mark.anyio
    async def test_api_called_with_correct_sign(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', horóscopo escorpião')

        route = respx_mock.get(
            'https://freehoroscopeapi.com/api/v1/get-horoscope/daily',
            params={'sign': 'scorpio'},
        ).mock(
            return_value=httpx.Response(
                200, json={'data': {**MOCK_RESPONSE['data'], 'sign': 'Scorpio'}}
            )
        )
        respx_mock.get(url__startswith='https://translate.googleapis.com/translate_a/single').mock(
            return_value=httpx.Response(200, json=MOCK_TRANSLATION)
        )

        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_all_signs_accepted(self, command):
        signs = [
            'áries',
            'touro',
            'gêmeos',
            'câncer',
            'leão',
            'virgem',
            'libra',
            'escorpião',
            'sagitário',
            'capricórnio',
            'aquário',
            'peixes',
        ]
        for sign in signs:
            assert command.matches(f', horóscopo {sign}'), f'{sign} should match'
