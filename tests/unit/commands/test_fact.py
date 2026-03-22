import httpx
import pytest

from bot.domain.commands.fact import FactCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory

RANDOM_URL = 'https://uselessfacts.jsph.pl/api/v2/facts/random'
TODAY_URL = 'https://uselessfacts.jsph.pl/api/v2/facts/today'


@pytest.fixture
def command():
    return FactCommand()


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
    async def test_calls_random_endpoint_by_default(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', fato')
        route = respx_mock.get(RANDOM_URL).mock(
            return_value=httpx.Response(200, json={'text': 'A random fact'})
        )
        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_calls_today_endpoint_with_hoje_flag(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', fato hoje')
        route = respx_mock.get(TODAY_URL).mock(
            return_value=httpx.Response(200, json={'text': 'Today fact'})
        )
        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_returns_formatted_text(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', fato')
        respx_mock.get(RANDOM_URL).mock(
            return_value=httpx.Response(200, json={'text': 'Cats sleep 70% of their lives.'})
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'FATO' in messages[0].content.text
        assert 'Cats sleep 70% of their lives.' in messages[0].content.text

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', fato', message_id='MSG_42')
        respx_mock.get(RANDOM_URL).mock(return_value=httpx.Response(200, json={'text': 'A fact'}))
        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_includes_expiration(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', fato', expiration=86400)
        respx_mock.get(RANDOM_URL).mock(return_value=httpx.Response(200, json={'text': 'A fact'}))
        messages = await command.run(data)

        assert messages[0].expiration == 86400
