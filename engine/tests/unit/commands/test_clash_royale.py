import pytest

from bot.domain.commands.clash_royale import ClashRoyaleCommand
from bot.domain.models.message import ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return ClashRoyaleCommand()


def _mock_cards_response():
    cards = [
        {
            'key': 'knight',
            'name': 'Knight',
            'elixir': 3,
            'type': 'Troop',
            'rarity': 'Common',
            'arena': 0,
            'description': 'A tough melee fighter.',
        }
    ]
    return make_json_response(cards)


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', cr', True),
            (',cr', True),
            (', CR', True),
            (', cr show', True),
            (', cr dm', True),
            ('  , cr  ', True),
            ('cr', False),
            ('hello', False),
            (', cr extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_api(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', cr')
        mock_resp = _mock_cards_response()

        mock_get = mocker.patch(
            'bot.domain.commands.clash_royale.HttpClient.get', return_value=mock_resp
        )
        await command.run(data)

        mock_get.assert_called_once()

    @pytest.mark.anyio
    async def test_returns_image_with_card_info(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', cr')
        mock_resp = _mock_cards_response()

        mocker.patch('bot.domain.commands.clash_royale.HttpClient.get', return_value=mock_resp)
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert 'knight.png' in messages[0].content.url
        caption = messages[0].content.caption
        assert 'Knight' in caption
        assert 'Troop' in caption
        assert 'Common' in caption
        assert 'Arena 0' in caption

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', cr')

        mocker.patch(
            'bot.domain.commands.clash_royale.HttpClient.get',
            side_effect=Exception('API down'),
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text
