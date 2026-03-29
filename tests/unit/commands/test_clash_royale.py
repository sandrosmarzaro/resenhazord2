import httpx
import pytest

from bot.domain.commands.clash_royale import ClashRoyaleCommand
from bot.domain.models.message import ImageBufferContent, ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory

CARDS_API_URL = 'https://royaleapi.github.io/cr-api-data/json/cards.json'
ASSETS_BASE = 'https://raw.githubusercontent.com/RoyaleAPI/cr-api-assets/master/cards/'

MOCK_CARDS = [
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

MOCK_DECK_CARDS = [
    {'key': f'card{i}', 'name': f'Card {i}', 'elixir': i % 10, 'rarity': 'Common'} for i in range(8)
]


@pytest.fixture
def command():
    return ClashRoyaleCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', cr', True),
            (',cr', True),
            (', CR', True),
            (', cr show', True),
            (', cr dm', True),
            (', cr deck', True),
            ('  , cr  ', True),
            (', clashroyale', True),
            (',clashroyale', True),
            ('cr', False),
            ('hello', False),
            (', cr extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_api(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cr')
        route = respx_mock.get(CARDS_API_URL).mock(
            return_value=httpx.Response(200, json=MOCK_CARDS)
        )
        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_returns_image_with_card_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cr')
        respx_mock.get(CARDS_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARDS))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert 'knight.png' in messages[0].content.url
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Knight' in caption
        assert 'Troop' in caption
        assert 'Common' in caption
        assert 'Arena 0' in caption

    @pytest.mark.anyio
    async def test_returns_error_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', cr')
        respx_mock.get(CARDS_API_URL).mock(side_effect=Exception('API down'))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro' in messages[0].content.text


class TestDeck:
    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', cr deck')
        respx_mock.get(CARDS_API_URL).mock(return_value=httpx.Response(200, json=MOCK_DECK_CARDS))
        respx_mock.get(url__startswith=ASSETS_BASE).mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_caption_has_numbered_cards(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', cr deck')
        respx_mock.get(CARDS_API_URL).mock(return_value=httpx.Response(200, json=MOCK_DECK_CARDS))
        respx_mock.get(url__startswith=ASSETS_BASE).mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*1.*' in caption
        assert 'Card 0' in caption
