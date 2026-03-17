from unittest.mock import MagicMock, patch

import pytest

from bot.domain.commands.biblia import BibliaCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return BibliaCommand()


def _mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


def _verse_response(**overrides):
    return {
        'book': {'name': 'Gênesis'},
        'chapter': 1,
        'number': 1,
        'text': 'No princípio, Deus criou os céus e a terra.',
        **overrides,
    }


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', bíblia', True),
            (',bíblia', True),
            (', biblia', True),
            (', BÍBLIA', True),
            (', bíblia nvi', True),
            (', bíblia kjv', True),
            (', bíblia Gênesis 1:1', True),
            ('  , bíblia  ', True),
            ('bíblia', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_random_verse_when_no_args(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia')
        mock_resp = _mock_response(_verse_response())

        with patch('bot.domain.commands.biblia.HttpClient.get', return_value=mock_resp) as mock_get:
            messages = await command.run(data)

            url = mock_get.call_args[0][0]
            assert '/random' in url

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Gênesis 1:1' in messages[0].content.text

    @pytest.mark.anyio
    async def test_uses_specified_version(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia kjv')
        mock_resp = _mock_response(_verse_response())

        with patch('bot.domain.commands.biblia.HttpClient.get', return_value=mock_resp) as mock_get:
            await command.run(data)

            url = mock_get.call_args[0][0]
            assert '/kjv/' in url

    @pytest.mark.anyio
    async def test_specific_verse(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia Gênesis 1:1')
        books_resp = _mock_response([{'name': 'Gênesis', 'abbrev': {'pt': 'gn'}}])
        verse_resp = _mock_response(_verse_response())

        with patch(
            'bot.domain.commands.biblia.HttpClient.get',
            side_effect=[books_resp, verse_resp],
        ) as mock_get:
            messages = await command.run(data)

            verse_url = mock_get.call_args_list[1][0][0]
            assert '/gn/' in verse_url

        assert 'Gênesis 1:1' in messages[0].content.text

    @pytest.mark.anyio
    async def test_book_not_found(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia Xablau 1:1')
        books_resp = _mock_response([{'name': 'Gênesis', 'abbrev': {'pt': 'gn'}}])

        with patch('bot.domain.commands.biblia.HttpClient.get', return_value=books_resp):
            messages = await command.run(data)

        assert 'Não consegui encontrar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_missing_book_name_returns_error(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia 1:1')

        messages = await command.run(data)

        assert 'Por favor, digite o nome' in messages[0].content.text

    @pytest.mark.anyio
    async def test_verse_range(self, command):
        data = GroupCommandDataFactory.build(text=', bíblia Gênesis 1:1-3')
        books_resp = _mock_response([{'name': 'Gênesis', 'abbrev': {'pt': 'gn'}}])
        verse1 = _mock_response({'text': 'Verso 1'})
        verse2 = _mock_response({'text': 'Verso 2'})
        verse3 = _mock_response({'text': 'Verso 3'})

        with patch(
            'bot.domain.commands.biblia.HttpClient.get',
            side_effect=[books_resp, verse1, verse2, verse3],
        ):
            messages = await command.run(data)

        text = messages[0].content.text
        assert 'Gênesis 1:1-3' in text
        assert 'Verso 1' in text
        assert 'Verso 3' in text
