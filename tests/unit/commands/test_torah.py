import httpx
import pytest

from bot.domain.commands.torah import TorahCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory

TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'


@pytest.fixture
def command():
    return TorahCommand()


def _sefaria_response(**overrides):
    return {
        'ref': 'Genesis 1:1',
        'heTitle': 'בראשית',
        'text': 'In the beginning God created the heaven and the earth.',
        'he': 'בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים',
        **overrides,
    }


def _mock_translate(respx_mock, translated='No início Deus criou os céus e a terra.'):
    respx_mock.get(url__startswith=TRANSLATE_URL).mock(
        return_value=httpx.Response(200, json=[[[translated, 'original']]])
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', torá', True),
            (',torá', True),
            (', TORÁ', True),
            (', tora', True),
            (', torá he', True),
            (', torá en', True),
            (', torá pt', True),
            (', torá Genesis 1:1', True),
            ('  , torá  ', True),
            ('torá', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_random_verse_returns_hebrew_and_portuguese(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá')
        respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(200, json=_sefaria_response())
        )
        _mock_translate(respx_mock)
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        text = messages[0].content.text
        assert 'Genesis 1:1' in text
        assert 'בראשית' in text
        assert 'No início' in text

    @pytest.mark.anyio
    async def test_hebrew_only_with_he_option(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá he')
        respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(200, json=_sefaria_response())
        )
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'בְּרֵאשִׁ֖ית' in text
        assert 'beginning' not in text

    @pytest.mark.anyio
    async def test_english_only_with_en_option(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá en')
        respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(200, json=_sefaria_response())
        )
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'beginning' in text
        assert 'בְּרֵאשִׁ֖ית' not in text

    @pytest.mark.anyio
    async def test_portuguese_only_with_pt_option(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá pt')
        respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(200, json=_sefaria_response())
        )
        _mock_translate(respx_mock)
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'No início' in text
        assert 'בְּרֵאשִׁ֖ית' not in text
        assert 'beginning' not in text

    @pytest.mark.anyio
    async def test_specific_verse_with_args(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá Exodus 3:14')
        route = respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(200, json=_sefaria_response(ref='Exodus 3:14'))
        )
        _mock_translate(respx_mock)
        await command.run(data)

        url = str(route.calls.last.request.url)
        assert 'Exodus.3.14' in url

    @pytest.mark.anyio
    async def test_invalid_args_returns_books_list(self, command):
        data = GroupCommandDataFactory.build(text=', torá invalid')

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'Livros da Torá' in messages[0].content.text

    @pytest.mark.anyio
    async def test_api_error_returns_books_list(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá')
        respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(200, json=_sefaria_response(error='Not found'))
        )
        messages = await command.run(data)

        assert 'Livros da Torá' in messages[0].content.text

    @pytest.mark.anyio
    async def test_empty_verse_returns_books_list(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá')
        respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(200, json=_sefaria_response(he='', text=''))
        )
        messages = await command.run(data)

        assert 'Livros da Torá' in messages[0].content.text

    @pytest.mark.anyio
    async def test_list_verse_content_joined(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', torá')
        respx_mock.get(url__startswith='https://www.sefaria.org/api/texts/').mock(
            return_value=httpx.Response(
                200,
                json=_sefaria_response(he=['<b>part1</b>', 'part2'], text=['hello', 'world']),
            )
        )
        _mock_translate(respx_mock, 'olá mundo')
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'part1 part2' in text
        assert 'olá mundo' in text
