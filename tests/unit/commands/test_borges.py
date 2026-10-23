import pytest

from bot.domain.commands.borges import BorgesCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return BorgesCommand()


@pytest.fixture
def mock_increment(command, mocker):
    return mocker.patch.object(command.COUNTER, 'increment', return_value=42)


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',borges', True),
            (', borges', True),
            (', BORGES', True),
            ('borges', False),
            ('hello', False),
            (', borges extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_count(self, command, mock_increment):
        data = GroupCommandDataFactory.build(text=',borges')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Borges já fumou 42 nargas 🚬' in messages[0].content.text

    @pytest.mark.anyio
    async def test_counts_by_message_id(self, command, mock_increment):
        data = GroupCommandDataFactory.build(text=',borges', message_id='MSG-1')

        await command.run(data)

        mock_increment.assert_called_once_with('MSG-1')
