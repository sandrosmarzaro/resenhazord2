import pytest
from telegram.constants import ChatType

from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from tests.unit.adapters.telegram.conftest import (
    make_mention_update,
    make_strategy,
    make_update,
    patch_registry,
    stub_agent_executor,
)


def _ok_message() -> BotMessage:
    return BotMessage(jid='1', content=TextContent(text='pong'))


class TestDmAgentMode:
    @pytest.mark.anyio
    async def test_dm_without_command_triggers_agent(self, handler, port, mocker):
        strategy = make_strategy(mocker, messages=[_ok_message()])
        patch_registry(mocker, strategy=strategy)
        executor = stub_agent_executor(mocker, returns_text=',d20')

        await handler.handle(port, make_update('me mande o g4 do Brasileirão'))

        executor.run.assert_called_once()
        call_data = executor.run.call_args.args[0]
        assert call_data.is_group is False
        port.send.assert_called()

    @pytest.mark.anyio
    async def test_dm_unknown_command_replied(self, handler, port, mocker):
        patch_registry(mocker, strategy=None)
        stub_agent_executor(mocker, returns_text=',foo')

        await handler.handle(port, make_update('foo bar baz'))

        sent = port.send.call_args.args[0]
        assert sent.text == handler.UNKNOWN_COMMAND_MESSAGE


class TestGroupAgentMention:
    @pytest.mark.anyio
    async def test_group_without_mention_ignored(self, handler, port, mocker):
        await handler.handle(port, make_update('hello world', chat_type=ChatType.GROUP))

        port.send.assert_not_called()

    @pytest.mark.anyio
    async def test_group_with_mention_triggers_agent(self, handler, port, mocker):
        strategy = make_strategy(mocker, messages=[_ok_message()])
        patch_registry(mocker, strategy=strategy)
        executor = stub_agent_executor(mocker, returns_text=',d20')

        await handler.handle(port, make_mention_update('@resenhazord_bot oi', mention_length=16))

        executor.run.assert_called_once()
        port.send.assert_called()
