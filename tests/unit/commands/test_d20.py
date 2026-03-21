import re

import pytest

from bot.domain.commands.d20 import D20Command
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command():
    return D20Command()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', d20', True),
            (',d20', True),
            (', D20', True),
            (',D20', True),
            ('  , d20  ', True),
            ('d20', False),
            (', d20 extra', False),
            (', d200', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_message_with_dice_roll(self, command):
        data = GroupCommandDataFactory.build(text=', d20')

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].jid == data.jid
        assert isinstance(messages[0].content, TextContent)
        assert re.search(r'Aqui está sua rolada: \d+ 🎲', messages[0].content.text)

    @pytest.mark.anyio
    async def test_roll_between_1_and_20(self, command):
        data = GroupCommandDataFactory.build(text=', d20')

        messages = await command.run(data)

        match = re.search(r': (\d+)', messages[0].content.text)
        assert match is not None
        roll = int(match.group(1))
        assert 1 <= roll <= 20

    @pytest.mark.anyio
    async def test_returns_random_values(self, command):
        data = GroupCommandDataFactory.build(text=', d20')
        results = set()

        for _ in range(100):
            messages = await command.run(data)
            match = re.search(r': (\d+)', messages[0].content.text)
            assert match is not None
            results.add(int(match.group(1)))

        assert len(results) > 1

    @pytest.mark.anyio
    async def test_works_in_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=', d20')

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].jid == data.jid

    @pytest.mark.anyio
    async def test_includes_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', d20', expiration=86400)

        messages = await command.run(data)

        assert messages[0].expiration == 86400

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', d20', message_id='MSG_42')

        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'
