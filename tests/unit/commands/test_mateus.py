import re

import pytest

from bot.domain.commands.mateus import MateusCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return MateusCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', mateus', True),
            (',mateus', True),
            (', MATEUS', True),
            (',MATEUS', True),
            ('  , mateus  ', True),
            ('mateus', False),
            ('hello', False),
            (', mateus test', False),
            (', mateusinho', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_probability_in_format(self, command):
        data = GroupCommandDataFactory.build(text=', mateus')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert re.search(r'\d{1,3},\d{2} %', messages[0].content.text)

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', mateus', message_id='MSG_42')

        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_includes_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', mateus', expiration=86400)

        messages = await command.run(data)

        assert messages[0].expiration == 86400
