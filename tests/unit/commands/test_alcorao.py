import httpx
import pytest

from bot.domain.commands.alcorao import AlcoraoCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return AlcoraoCommand()


MOCK_EDITIONS = {
    'data': [
        {
            'text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
            'numberInSurah': 1,
            'surah': {'englishName': 'Al-Fatiha', 'number': 1},
        },
        {
            'text': 'Em nome de Deus, o Clemente, o Misericordioso.',
            'numberInSurah': 1,
            'surah': {'englishName': 'Al-Fatiha', 'number': 1},
        },
    ]
}


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', alcorão', True),
            (',alcorão', True),
            (', ALCORÃO', True),
            (', alcorao', True),
            (', alcorão ar', True),
            (', alcorão pt', True),
            ('  , alcorão  ', True),
            ('alcorão', False),
            ('hello', False),
            (', alcorão extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_editions_api(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão')
        route = respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_EDITIONS)
        )

        await command.run(data)

        assert route.called
        url = str(route.calls.last.request.url)
        assert '/editions/ar.alafasy,pt.elhayek' in url

    @pytest.mark.anyio
    async def test_returns_both_languages_by_default(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão')
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_EDITIONS)
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        text = messages[0].content.text
        assert 'Al-Fatiha' in text
        assert '1:1' in text
        assert 'بِسْمِ اللَّهِ' in text
        assert 'Em nome de Deus' in text

    @pytest.mark.anyio
    async def test_arabic_only_with_ar_option(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão ar')
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_EDITIONS)
        )

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'بِسْمِ اللَّهِ' in text
        assert 'Em nome de Deus' not in text

    @pytest.mark.anyio
    async def test_portuguese_only_with_pt_option(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão pt')
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_EDITIONS)
        )

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Em nome de Deus' in text
        assert 'بِسْمِ اللَّهِ' not in text

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão', message_id='MSG_42')
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_EDITIONS)
        )

        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_includes_expiration(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão', expiration=86400)
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_EDITIONS)
        )

        messages = await command.run(data)

        assert messages[0].expiration == 86400
