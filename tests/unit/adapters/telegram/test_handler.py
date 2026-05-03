import pytest
from telegram.constants import ChatType

from bot.adapters.telegram.agent_router import TelegramAgentRouter
from bot.domain.commands.base import CommandScope, Platform
from bot.domain.exceptions import BotError
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from bot.ports.telegram_port import TelegramKind
from tests.unit.adapters.telegram.conftest import (
    DEFAULT_CHAT_ID,
    make_strategy,
    make_update,
    patch_registry,
)


def _ok_message() -> BotMessage:
    return BotMessage(jid='1', content=TextContent(text='pong'))


class TestDispatch:
    @pytest.mark.anyio
    async def test_runs_strategy_and_sends_outbounds(self, handler, port, mocker):
        strategy = make_strategy(mocker, messages=[_ok_message()])
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/d20'))

        port.send_typing.assert_called_once_with(DEFAULT_CHAT_ID)
        port.react.assert_called_once_with(DEFAULT_CHAT_ID, 1, TelegramAgentRouter.ACK_REACTION)
        assert any(
            call.args[0].kind == TelegramKind.TEXT and call.args[0].text == 'pong'
            for call in port.send.call_args_list
        )

    @pytest.mark.anyio
    async def test_react_failure_does_not_block_command(self, handler, port, mocker):
        strategy = make_strategy(mocker, messages=[_ok_message()])
        patch_registry(mocker, strategy=strategy)
        port.react.side_effect = RuntimeError('boom')

        await handler.handle(port, make_update('/d20'))

        data = strategy.run.call_args.args[0]
        assert data.platform == Platform.TELEGRAM
        assert data.jid == str(DEFAULT_CHAT_ID)
        assert data.text == ',d20'

    @pytest.mark.anyio
    async def test_unknown_command_does_not_react(self, handler, port, mocker):
        patch_registry(mocker, strategy=None)

        await handler.handle(port, make_update('/missing'))

        port.react.assert_not_called()

    @pytest.mark.anyio
    async def test_unknown_command_replies_not_recognized(self, handler, port, mocker):
        patch_registry(mocker, strategy=None)

        await handler.handle(port, make_update('/missing'))

        sent = port.send.call_args.args[0]
        assert sent.kind == TelegramKind.TEXT
        assert sent.text == handler.UNKNOWN_COMMAND_MESSAGE


class TestMentionStripping:
    @pytest.mark.anyio
    async def test_strips_own_bot_mention_in_group(self, handler, port, mocker):
        strategy = make_strategy(mocker)
        registry = patch_registry(mocker, strategy=strategy)

        await handler.handle(
            port, make_update('/d20@resenhazord_bot 2d6', chat_type=ChatType.GROUP)
        )

        assert registry.get_strategy.call_args.args[0] == ',d20 2d6'

    @pytest.mark.anyio
    async def test_foreign_bot_mention_preserved(self, handler, port, mocker):
        strategy = make_strategy(mocker)
        registry = patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/d20@other_bot'))

        assert registry.get_strategy.call_args.args[0].startswith(',d20@other_bot')


class TestScopeAndAccess:
    @pytest.mark.anyio
    async def test_group_only_refused_in_dm(self, handler, port, mocker):
        strategy = make_strategy(mocker, group_only=True)
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/groupcmd'))

        sent = port.send.call_args.args[0]
        assert sent.text == handler.GROUP_ONLY_MESSAGE

    @pytest.mark.anyio
    async def test_nsfw_refused_outside_allowlist(self, handler, port, mocker):
        strategy = make_strategy(mocker, scope=CommandScope.NSFW)
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/hentai', chat_id=123))

        sent = port.send.call_args.args[0]
        assert sent.text == handler.NSFW_ONLY_MESSAGE

    @pytest.mark.anyio
    async def test_nsfw_allowed_in_allowlisted_chat(self, handler, port, mocker):
        strategy = make_strategy(
            mocker,
            scope=CommandScope.NSFW,
            messages=[BotMessage(jid='99', content=TextContent(text='ok'))],
        )
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/hentai', chat_id=99))

        strategy.run.assert_called_once()


class TestErrorHandling:
    @pytest.mark.anyio
    async def test_bot_error_replies_user_message(self, handler, port, mocker):
        strategy = make_strategy(mocker)
        strategy.run = mocker.AsyncMock(side_effect=BotError(user_message='oops'))
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/boom'))

        sent = port.send.call_args.args[0]
        assert sent.text == 'oops'

    @pytest.mark.anyio
    async def test_generic_exception_replies_generic_error(self, handler, port, mocker):
        strategy = make_strategy(mocker)
        strategy.run = mocker.AsyncMock(side_effect=RuntimeError('boom'))
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/crash'))

        sent = port.send.call_args.args[0]
        assert sent.text == TelegramAgentRouter.GENERIC_ERROR_MESSAGE

    @pytest.mark.anyio
    async def test_empty_messages_replies_empty(self, handler, port, mocker):
        strategy = make_strategy(mocker, messages=[])
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/silent'))

        sent = port.send.call_args.args[0]
        assert sent.text == TelegramAgentRouter.EMPTY_REPLY_MESSAGE

    @pytest.mark.anyio
    async def test_non_command_in_group_ignored(self, handler, port, mocker):
        patch_registry(mocker, strategy=None)

        await handler.handle(port, make_update('just some text', chat_type=ChatType.GROUP))

        port.send.assert_not_called()
