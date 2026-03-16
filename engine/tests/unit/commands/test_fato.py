from unittest.mock import MagicMock, patch

import pytest

from bot.domain.commands.fato import FatoCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return FatoCommand()


def _mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', fato', True),
            (',fato', True),
            (', FATO', True),
            (', fato hoje', True),
            (',fato hoje', True),
            ('  , fato  ', True),
            ('fato', False),
            ('hello', False),
            (', fato extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_random_endpoint_by_default(self, command):
        data = GroupCommandDataFactory.build(text=', fato')
        mock_resp = _mock_response({'text': 'A random fact'})

        with patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp) as mock_get:
            await command.run(data)

            mock_get.assert_called_once_with('https://uselessfacts.jsph.pl/api/v2/facts/random')

    @pytest.mark.anyio
    async def test_calls_today_endpoint_with_hoje_flag(self, command):
        data = GroupCommandDataFactory.build(text=', fato hoje')
        mock_resp = _mock_response({'text': 'Today fact'})

        with patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp) as mock_get:
            await command.run(data)

            mock_get.assert_called_once_with('https://uselessfacts.jsph.pl/api/v2/facts/today')

    @pytest.mark.anyio
    async def test_returns_formatted_text(self, command):
        data = GroupCommandDataFactory.build(text=', fato')
        mock_resp = _mock_response({'text': 'Cats sleep 70% of their lives.'})

        with patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'FATO' in messages[0].content.text
        assert 'Cats sleep 70% of their lives.' in messages[0].content.text

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', fato', message_id='MSG_42')
        mock_resp = _mock_response({'text': 'A fact'})

        with patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_includes_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', fato', expiration=86400)
        mock_resp = _mock_response({'text': 'A fact'})

        with patch('bot.domain.commands.fato.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert messages[0].expiration == 86400
