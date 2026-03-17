from unittest.mock import MagicMock, patch

import pytest

from bot.domain.commands.torah import TorahCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return TorahCommand()


def _mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


def _sefaria_response(**overrides):
    return {
        'ref': 'Genesis 1:1',
        'heTitle': 'בראשית',
        'text': 'In the beginning God created the heaven and the earth.',
        'he': 'בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים',
        **overrides,
    }


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
    async def test_random_verse_returns_both_languages(self, command):
        data = GroupCommandDataFactory.build(text=', torá')
        mock_resp = _mock_response(_sefaria_response())

        with patch('bot.domain.commands.torah.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        text = messages[0].content.text
        assert 'Genesis 1:1' in text
        assert 'בראשית' in text
        assert 'beginning' in text

    @pytest.mark.anyio
    async def test_hebrew_only_with_he_option(self, command):
        data = GroupCommandDataFactory.build(text=', torá he')
        mock_resp = _mock_response(_sefaria_response())

        with patch('bot.domain.commands.torah.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        text = messages[0].content.text
        assert 'בְּרֵאשִׁ֖ית' in text
        assert 'beginning' not in text

    @pytest.mark.anyio
    async def test_english_only_with_en_option(self, command):
        data = GroupCommandDataFactory.build(text=', torá en')
        mock_resp = _mock_response(_sefaria_response())

        with patch('bot.domain.commands.torah.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        text = messages[0].content.text
        assert 'beginning' in text
        assert 'בְּרֵאשִׁ֖ית' not in text

    @pytest.mark.anyio
    async def test_specific_verse_with_args(self, command):
        data = GroupCommandDataFactory.build(text=', torá Exodus 3:14')
        mock_resp = _mock_response(_sefaria_response(ref='Exodus 3:14'))

        with patch('bot.domain.commands.torah.HttpClient.get', return_value=mock_resp) as mock_get:
            await command.run(data)

            url = mock_get.call_args[0][0]
            assert 'Exodus.3.14' in url

    @pytest.mark.anyio
    async def test_invalid_args_returns_books_list(self, command):
        data = GroupCommandDataFactory.build(text=', torá invalid')

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'Livros da Torá' in messages[0].content.text

    @pytest.mark.anyio
    async def test_api_error_returns_books_list(self, command):
        data = GroupCommandDataFactory.build(text=', torá')
        mock_resp = _mock_response(_sefaria_response(error='Not found'))

        with patch('bot.domain.commands.torah.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert 'Livros da Torá' in messages[0].content.text

    @pytest.mark.anyio
    async def test_empty_verse_returns_books_list(self, command):
        data = GroupCommandDataFactory.build(text=', torá')
        mock_resp = _mock_response(_sefaria_response(he='', text=''))

        with patch('bot.domain.commands.torah.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert 'Livros da Torá' in messages[0].content.text

    @pytest.mark.anyio
    async def test_list_verse_content_joined(self, command):
        data = GroupCommandDataFactory.build(text=', torá')
        mock_resp = _mock_response(
            _sefaria_response(he=['<b>part1</b>', 'part2'], text=['hello', 'world'])
        )

        with patch('bot.domain.commands.torah.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        text = messages[0].content.text
        assert 'part1 part2' in text
        assert 'hello world' in text
