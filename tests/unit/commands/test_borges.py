import pytest

from bot.domain.commands.borges import BorgesCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return BorgesCommand()


@pytest.fixture
def mock_collection(mock_mongodb_collection):
    return mock_mongodb_collection('borges')


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
    async def test_increments_and_returns_count(self, command, mock_collection):
        mock_collection.find_one_and_update.return_value = {'_id': 'counter', 'nargas': 42}
        data = GroupCommandDataFactory.build(text=',borges')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Borges já fumou 42 nargas 🚬' in messages[0].content.text

    @pytest.mark.anyio
    async def test_calls_find_one_and_update_with_upsert(self, command, mock_collection):
        mock_collection.find_one_and_update.return_value = {'nargas': 1}
        data = GroupCommandDataFactory.build(text=',borges')

        await command.run(data)

        mock_collection.find_one_and_update.assert_called_once_with(
            {'_id': 'counter'},
            {'$inc': {'nargas': 1}},
            return_document=True,
            upsert=True,
        )

    @pytest.mark.anyio
    async def test_first_call_shows_one(self, command, mock_collection):
        mock_collection.find_one_and_update.return_value = {'nargas': 1}
        data = GroupCommandDataFactory.build(text=',borges')

        messages = await command.run(data)

        assert '1 nargas' in messages[0].content.text
