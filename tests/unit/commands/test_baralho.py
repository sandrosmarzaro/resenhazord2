import httpx
import pytest

from bot.domain.commands.baralho import BaralhoCommand
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory

DECK_API_URL = 'https://deckofcardsapi.com/api/deck/new/draw/?count=1'


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
    async def test_calls_api(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', carta')
        route = respx_mock.get(DECK_API_URL).mock(
            return_value=httpx.Response(
                200, json={'cards': [{'image': 'https://example.com/card.png'}]}
            )
        )
        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_returns_image_with_caption(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', carta')
        respx_mock.get(DECK_API_URL).mock(
            return_value=httpx.Response(
                200, json={'cards': [{'image': 'https://example.com/card.png'}]}
            )
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/card.png'
        assert messages[0].content.caption is not None
        assert 'carta' in messages[0].content.caption.lower()

    @pytest.mark.anyio
    async def test_image_is_view_once(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', carta')
        respx_mock.get(DECK_API_URL).mock(
            return_value=httpx.Response(
                200, json={'cards': [{'image': 'https://example.com/card.png'}]}
            )
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', carta', message_id='MSG_42')
        respx_mock.get(DECK_API_URL).mock(
            return_value=httpx.Response(
                200, json={'cards': [{'image': 'https://example.com/card.png'}]}
            )
        )
        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'
