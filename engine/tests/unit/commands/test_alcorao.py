from unittest.mock import MagicMock, patch

import pytest

from bot.domain.commands.alcorao import AlcoraoCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return AlcoraoCommand()


def _mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


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
    async def test_calls_api(self, command):
        data = GroupCommandDataFactory.build(text=', alcorão')
        mock_resp = _mock_response(
            {
                'data': {
                    'text': 'In the name of God',
                    'numberInSurah': 1,
                    'surah': {'englishName': 'Al-Fatiha', 'number': 1},
                }
            }
        )

        with patch(
            'bot.domain.commands.alcorao.HttpClient.get', return_value=mock_resp
        ) as mock_get:
            await command.run(data)

            url = mock_get.call_args[0][0]
            assert url.startswith('https://api.alquran.cloud/v1/ayah/')
            assert url.endswith('/pt.elhayek')

    @pytest.mark.anyio
    async def test_returns_formatted_text(self, command):
        data = GroupCommandDataFactory.build(text=', alcorão')
        mock_resp = _mock_response(
            {
                'data': {
                    'text': 'In the name of God',
                    'numberInSurah': 1,
                    'surah': {'englishName': 'Al-Fatiha', 'number': 1},
                }
            }
        )

        with patch('bot.domain.commands.alcorao.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Al-Fatiha' in messages[0].content.text
        assert '1:1' in messages[0].content.text
        assert 'In the name of God' in messages[0].content.text

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', alcorão', message_id='MSG_42')
        mock_resp = _mock_response(
            {
                'data': {
                    'text': 'verse',
                    'numberInSurah': 5,
                    'surah': {'englishName': 'Al-Baqara', 'number': 2},
                }
            }
        )

        with patch('bot.domain.commands.alcorao.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_includes_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', alcorão', expiration=86400)
        mock_resp = _mock_response(
            {
                'data': {
                    'text': 'verse',
                    'numberInSurah': 5,
                    'surah': {'englishName': 'Al-Baqara', 'number': 2},
                }
            }
        )

        with patch('bot.domain.commands.alcorao.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert messages[0].expiration == 86400
