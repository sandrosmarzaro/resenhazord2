import pytest
from telegram.constants import ChatType

from bot.adapters.telegram.agent_router import TelegramAgentRouter
from bot.domain.exceptions import BotError
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


class TestIsAgentMention:
    def test_detects_mention_in_text(self, mocker):
        msg = mocker.MagicMock()
        msg.text = 'hello @resenhazord_bot'
        assert TelegramAgentRouter.is_agent_mention(msg, 'resenhazord_bot') is True

    def test_case_insensitive_mention(self, mocker):
        msg = mocker.MagicMock()
        msg.text = 'hello @RESENHAZORD_BOT'
        assert TelegramAgentRouter.is_agent_mention(msg, 'resenhazord_bot') is True

    def test_no_mention_returns_false(self, mocker):
        msg = mocker.MagicMock()
        msg.text = 'hello world'
        assert TelegramAgentRouter.is_agent_mention(msg, 'resenhazord_bot') is False

    def test_empty_text_returns_false(self, mocker):
        msg = mocker.MagicMock()
        msg.text = None
        assert TelegramAgentRouter.is_agent_mention(msg, 'resenhazord_bot') is False

    def test_empty_bot_username_returns_false(self, mocker):
        msg = mocker.MagicMock()
        msg.text = 'hello @bot'
        assert TelegramAgentRouter.is_agent_mention(msg, '') is False


class TestSafeReact:
    @pytest.mark.anyio
    async def test_reacts_successfully(self, port):
        await TelegramAgentRouter.safe_react(port, 123, 456)

        port.react.assert_called_once_with(123, 456, '\U0001f44d')

    @pytest.mark.anyio
    async def test_react_failure_is_swallowed(self, port):
        port.react.side_effect = Exception('react failed')

        await TelegramAgentRouter.safe_react(port, 123, 456)

        port.react.assert_called_once()


class TestRunAndReply:
    @pytest.mark.anyio
    async def test_bot_error_sends_user_message(self, mocker, port):
        renderer = mocker.MagicMock()
        renderer.render_many.return_value = []
        router = TelegramAgentRouter(renderer)
        strategy = mocker.MagicMock()
        strategy.run = mocker.AsyncMock(side_effect=BotError('custom error'))

        await router.run_and_reply(port, strategy, mocker.MagicMock(), 123, 'cmd')

        sent = port.send.call_args.args[0]
        assert sent.text == 'custom error'

    @pytest.mark.anyio
    async def test_generic_error_sends_generic_message(self, mocker, port):
        renderer = mocker.MagicMock()
        router = TelegramAgentRouter(renderer)
        strategy = mocker.MagicMock()
        strategy.run = mocker.AsyncMock(side_effect=RuntimeError('boom'))

        await router.run_and_reply(port, strategy, mocker.MagicMock(), 123, 'cmd')

        sent = port.send.call_args.args[0]
        assert sent.text == TelegramAgentRouter.GENERIC_ERROR_MESSAGE

    @pytest.mark.anyio
    async def test_empty_messages_sends_empty_reply(self, mocker, port):
        renderer = mocker.MagicMock()
        router = TelegramAgentRouter(renderer)
        strategy = mocker.MagicMock()
        strategy.run = mocker.AsyncMock(return_value=[])

        await router.run_and_reply(port, strategy, mocker.MagicMock(), 123, 'cmd')

        sent = port.send.call_args.args[0]
        assert sent.text == TelegramAgentRouter.EMPTY_REPLY_MESSAGE

    @pytest.mark.anyio
    async def test_successful_run_sends_messages(self, mocker, port):
        renderer = mocker.MagicMock()
        outbound = mocker.MagicMock()
        renderer.render_many.return_value = [outbound]
        router = TelegramAgentRouter(renderer)
        strategy = mocker.MagicMock()
        strategy.run = mocker.AsyncMock(return_value=[_ok_message()])
        mocker.patch(
            'bot.adapters.telegram.agent_router.preprocess_for_telegram',
            mocker.AsyncMock(return_value=[_ok_message()]),
        )

        await router.run_and_reply(port, strategy, mocker.MagicMock(), 123, 'cmd')

        port.send.assert_called()


class TestSendMessages:
    @pytest.mark.anyio
    async def test_send_failure_sends_error_and_returns(self, mocker, port):
        renderer = mocker.MagicMock()
        outbound = mocker.MagicMock()
        renderer.render_many.return_value = [outbound]
        router = TelegramAgentRouter(renderer)
        call_count = 0

        class SendFailedError(Exception):
            pass

        send_error = SendFailedError('send failed')

        def _send_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise send_error

        port.send.side_effect = _send_side_effect
        mocker.patch(
            'bot.adapters.telegram.agent_router.preprocess_for_telegram',
            mocker.AsyncMock(return_value=[mocker.MagicMock()]),
        )

        await router._send_messages(port, [mocker.MagicMock()], 123, 'cmd')

        assert call_count == 2
