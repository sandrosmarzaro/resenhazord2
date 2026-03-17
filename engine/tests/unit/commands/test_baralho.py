from unittest.mock import patch

import pytest

from bot.domain.commands.baralho import BaralhoCommand
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return BaralhoCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', carta', True),
            (',carta', True),
            (', CARTA', True),
            (', carta show', True),
            (', carta dm', True),
            ('  , carta  ', True),
            ('carta', False),
            ('hello', False),
            (', carta extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_api(self, command):
        data = GroupCommandDataFactory.build(text=', carta')
        mock_resp = make_json_response({'cards': [{'image': 'https://example.com/card.png'}]})

        with patch(
            'bot.domain.commands.baralho.HttpClient.get', return_value=mock_resp
        ) as mock_get:
            await command.run(data)

            mock_get.assert_called_once_with(
                'https://deckofcardsapi.com/api/deck/new/draw/?count=1'
            )

    @pytest.mark.anyio
    async def test_returns_image_with_caption(self, command):
        data = GroupCommandDataFactory.build(text=', carta')
        mock_resp = make_json_response({'cards': [{'image': 'https://example.com/card.png'}]})

        with patch('bot.domain.commands.baralho.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/card.png'
        assert 'carta' in messages[0].content.caption.lower()

    @pytest.mark.anyio
    async def test_image_is_view_once(self, command):
        data = GroupCommandDataFactory.build(text=', carta')
        mock_resp = make_json_response({'cards': [{'image': 'https://example.com/card.png'}]})

        with patch('bot.domain.commands.baralho.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', carta', message_id='MSG_42')
        mock_resp = make_json_response({'cards': [{'image': 'https://example.com/card.png'}]})

        with patch('bot.domain.commands.baralho.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'
