import pytest

from bot.domain.commands.fipe import FipeCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return FipeCommand()


class TestErrors:
    @pytest.mark.anyio
    async def test_returns_error_text_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=',fipe')
        respx_mock.get(url__startswith=FipeCommand.FIPE_BASE).mock(
            side_effect=Exception('Network error')
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'não consegui consultar a FIPE' in messages[0].content.text
