from datetime import UTC, datetime

import pytest

from bot.domain.commands.lua import LuaCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

KNOWN_FULL_MOON = datetime(2000, 1, 21, 4, 40, tzinfo=UTC)
KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)


@pytest.fixture
def command():
    return LuaCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', lua', True),
            (',lua', True),
            (', LUA', True),
            (', moon', True),
            (',moon', True),
            ('  , lua  ', True),
            ('lua', False),
            (', lua extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_single_text_message(self, command):
        data = GroupCommandDataFactory.build(text=', lua')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)

    @pytest.mark.anyio
    async def test_full_moon_date(self, command, mocker):
        mocker.patch(
            'bot.domain.commands.lua.datetime',
            wraps=datetime,
            now=mocker.Mock(return_value=KNOWN_FULL_MOON),
        )
        data = GroupCommandDataFactory.build(text=', lua')

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Lua Cheia' in text
        assert '🌕' in text

    @pytest.mark.anyio
    async def test_new_moon_date(self, command, mocker):
        mocker.patch(
            'bot.domain.commands.lua.datetime',
            wraps=datetime,
            now=mocker.Mock(return_value=KNOWN_NEW_MOON),
        )
        data = GroupCommandDataFactory.build(text=', lua')

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Lua Nova' in text
        assert '🌑' in text

    @pytest.mark.anyio
    async def test_output_contains_date(self, command, mocker):
        fixed = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
        mocker.patch(
            'bot.domain.commands.lua.datetime',
            wraps=datetime,
            now=mocker.Mock(return_value=fixed),
        )
        data = GroupCommandDataFactory.build(text=', lua')

        messages = await command.run(data)

        assert '21/03/2026' in messages[0].content.text

    @pytest.mark.anyio
    async def test_output_contains_illumination(self, command):
        data = GroupCommandDataFactory.build(text=', lua')

        messages = await command.run(data)

        assert 'Iluminação: ~' in messages[0].content.text

    @pytest.mark.anyio
    async def test_works_in_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=', lua')

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].jid == data.jid

    @pytest.mark.anyio
    async def test_includes_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', lua', expiration=86400)

        messages = await command.run(data)

        assert messages[0].expiration == 86400

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', lua', message_id='MSG_42')

        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'
