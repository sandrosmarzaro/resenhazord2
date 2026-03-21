import httpx
import pytest

from bot.domain.commands.alcorao import AlcoraoCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return AlcoraoCommand()


MOCK_VERSE = {
    'data': {
        'text': 'In the name of God',
        'numberInSurah': 1,
        'surah': {'englishName': 'Al-Fatiha', 'number': 1},
    }
}


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', alcorão', True),
            (',alcorão', True),
            (', ALCORÃO', True),
            (', alcorao', True),
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
    async def test_calls_api(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão')
        route = respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_VERSE)
        )
        await command.run(data)

        assert route.called
        url = str(route.calls.last.request.url)
        assert url.startswith('https://api.alquran.cloud/v1/ayah/')
        assert url.endswith('/pt.elhayek')

    @pytest.mark.anyio
    async def test_returns_formatted_text(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão')
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(200, json=MOCK_VERSE)
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Al-Fatiha' in messages[0].content.text
        assert '1:1' in messages[0].content.text
        assert 'In the name of God' in messages[0].content.text

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão', message_id='MSG_42')
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'data': {
                        'text': 'verse',
                        'numberInSurah': 5,
                        'surah': {'englishName': 'Al-Baqara', 'number': 2},
                    }
                },
            )
        )
        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_includes_expiration(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', alcorão', expiration=86400)
        respx_mock.get(url__startswith='https://api.alquran.cloud/v1/ayah/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'data': {
                        'text': 'verse',
                        'numberInSurah': 5,
                        'surah': {'englishName': 'Al-Baqara', 'number': 2},
                    }
                },
            )
        )
        messages = await command.run(data)

        assert messages[0].expiration == 86400
