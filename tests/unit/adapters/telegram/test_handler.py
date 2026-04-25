from __future__ import annotations

from datetime import UTC, datetime

import pytest
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.constants import ChatType, MessageEntityType

from bot.adapters.telegram.handler import TelegramUpdateHandler
from bot.domain.commands.base import CommandScope, Platform
from bot.domain.exceptions import BotError
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from bot.ports.telegram_port import TelegramKind

DEFAULT_CHAT_ID = 111222333
DEFAULT_USER_ID = 999888777


def make_update(text: str, *, chat_type: str = ChatType.PRIVATE, chat_id: int = DEFAULT_CHAT_ID):
    user = User(id=DEFAULT_USER_ID, first_name='TestUser', is_bot=False)
    chat = Chat(id=chat_id, type=chat_type)
    token_len = len(text.split(maxsplit=1)[0]) if text.strip() else 0
    entities = (
        (MessageEntity(type=MessageEntityType.BOT_COMMAND, offset=0, length=token_len),)
        if text.startswith('/') and token_len > 0
        else ()
    )
    message = Message(
        message_id=1,
        date=datetime.now(tz=UTC),
        chat=chat,
        from_user=user,
        text=text,
        entities=entities,
    )
    return Update(update_id=1, message=message)


def make_strategy(mocker, messages=None, *, group_only=False, scope=CommandScope.PUBLIC):
    strategy = mocker.MagicMock()
    strategy.run = mocker.AsyncMock(return_value=messages or [])
    strategy.config = mocker.MagicMock(group_only=group_only, scope=scope)
    return strategy


@pytest.fixture
def handler():
    return TelegramUpdateHandler(bot_username='resenhazord_bot', nsfw_chat_ids=frozenset({99}))


def patch_registry(mocker, *, strategy=None, by_name=None):
    registry = mocker.MagicMock()
    registry.get_strategy.return_value = strategy
    registry.get_by_name.return_value = by_name
    mocker.patch(
        'bot.adapters.telegram.handler.CommandRegistry.instance',
        return_value=registry,
    )
    return registry


class TestHandle:
    @pytest.mark.anyio
    async def test_dispatches_and_sends_renderer_outbounds(self, handler, port, mocker):
        strategy = make_strategy(
            mocker, messages=[BotMessage(jid='1', content=TextContent(text='pong'))]
        )
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/d20'))

        port.send_typing.assert_called_once_with(DEFAULT_CHAT_ID)
        port.react.assert_called_once_with(DEFAULT_CHAT_ID, 1, handler.ACK_REACTION)
        assert any(
            call.args[0].kind == TelegramKind.TEXT and call.args[0].text == 'pong'
            for call in port.send.call_args_list
        )

    @pytest.mark.anyio
    async def test_react_failure_does_not_block_command(self, handler, port, mocker):
        strategy = make_strategy(
            mocker, messages=[BotMessage(jid='1', content=TextContent(text='pong'))]
        )
        patch_registry(mocker, strategy=strategy)
        port.react.side_effect = RuntimeError('boom')

        await handler.handle(port, make_update('/d20'))

        data = strategy.run.call_args.args[0]
        assert data.platform == Platform.TELEGRAM
        assert data.jid == str(DEFAULT_CHAT_ID)
        assert data.text == ',d20'

    @pytest.mark.anyio
    async def test_does_not_react_for_unknown_command(self, handler, port, mocker):
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

    @pytest.mark.anyio
    async def test_strips_bot_mention_in_group(self, handler, port, mocker):
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
        assert sent.text == handler.GENERIC_ERROR_MESSAGE

    @pytest.mark.anyio
    async def test_empty_messages_replies_empty(self, handler, port, mocker):
        strategy = make_strategy(mocker, messages=[])
        patch_registry(mocker, strategy=strategy)

        await handler.handle(port, make_update('/silent'))

        sent = port.send.call_args.args[0]
        assert sent.text == handler.EMPTY_REPLY_MESSAGE

    @pytest.mark.anyio
    async def test_non_command_update_in_group_ignored(self, handler, port, mocker):
        patch_registry(mocker, strategy=None)

        await handler.handle(port, make_update('just some text', chat_type=ChatType.GROUP))

        port.send.assert_not_called()

    @pytest.mark.anyio
    async def test_agent_mention_in_group_triggers_agent(self, handler, port, mocker):
        strategy = make_strategy(
            mocker, messages=[BotMessage(jid='1', content=TextContent(text='pong'))]
        )
        patch_registry(mocker, strategy=strategy)
        executor = mocker.MagicMock()
        executor.run = mocker.AsyncMock(return_value=mocker.MagicMock(text=',d20'))
        mocker.patch(
            'bot.adapters.telegram.handler.AgentExecutor',
            return_value=executor,
        )

        user = User(id=DEFAULT_USER_ID, first_name='TestUser', is_bot=False)
        chat = Chat(id=DEFAULT_CHAT_ID, type=ChatType.GROUP)
        message = Message(
            message_id=1,
            date=datetime.now(tz=UTC),
            chat=chat,
            from_user=user,
            text='@resenhazord_bot oi',
            entities=(MessageEntity(type=MessageEntityType.MENTION, offset=0, length=16),),
        )
        await handler.handle(port, Update(update_id=1, message=message))

        executor.run.assert_called_once()
        port.send.assert_called()


class TestDmAgentMode:
    @pytest.fixture
    def handler(self):
        return TelegramUpdateHandler(bot_username='resenhazord_bot', nsfw_chat_ids=frozenset())

    @pytest.mark.anyio
    async def test_dm_without_command_triggers_agent(self, handler, port, mocker):
        strategy = make_strategy(
            mocker, messages=[BotMessage(jid='1', content=TextContent(text='pong'))]
        )
        patch_registry(mocker, strategy=strategy)
        executor = mocker.MagicMock()
        executor.run = mocker.AsyncMock(return_value=mocker.MagicMock(text=',d20'))
        mocker.patch(
            'bot.adapters.telegram.handler.AgentExecutor',
            return_value=executor,
        )

        user = User(id=DEFAULT_USER_ID, first_name='TestUser', is_bot=False)
        chat = Chat(id=DEFAULT_CHAT_ID, type=ChatType.PRIVATE)
        message = Message(
            message_id=1,
            date=datetime.now(tz=UTC),
            chat=chat,
            from_user=user,
            text='me mande o g4 do Brasileirão',
            entities=(),
        )
        await handler.handle(port, Update(update_id=1, message=message))

        executor.run.assert_called_once()
        call_data = executor.run.call_args.args[0]
        assert call_data.is_group is False
        port.send.assert_called()

    @pytest.mark.anyio
    async def test_dm_unknown_command_replied(self, handler, port, mocker):
        patch_registry(mocker, strategy=None)
        executor = mocker.MagicMock()
        executor.run = mocker.AsyncMock(return_value=mocker.MagicMock(text=',foo'))
        mocker.patch(
            'bot.adapters.telegram.handler.AgentExecutor',
            return_value=executor,
        )

        user = User(id=DEFAULT_USER_ID, first_name='TestUser', is_bot=False)
        chat = Chat(id=DEFAULT_CHAT_ID, type=ChatType.PRIVATE)
        message = Message(
            message_id=1,
            date=datetime.now(tz=UTC),
            chat=chat,
            from_user=user,
            text='foo bar baz',
            entities=(),
        )
        await handler.handle(port, Update(update_id=1, message=message))

        sent = port.send.call_args.args[0]
        assert sent.text == handler.UNKNOWN_COMMAND_MESSAGE

    @pytest.mark.anyio
    async def test_group_without_mention_ignored(self, handler, port, mocker):
        user = User(id=DEFAULT_USER_ID, first_name='TestUser', is_bot=False)
        chat = Chat(id=DEFAULT_CHAT_ID, type=ChatType.GROUP)
        message = Message(
            message_id=1,
            date=datetime.now(tz=UTC),
            chat=chat,
            from_user=user,
            text='hello world',
            entities=(),
        )
        await handler.handle(port, Update(update_id=1, message=message))

        port.send.assert_not_called()

    @pytest.mark.anyio
    async def test_group_with_mention_still_triggers_agent(self, handler, port, mocker):
        strategy = make_strategy(
            mocker, messages=[BotMessage(jid='1', content=TextContent(text='pong'))]
        )
        patch_registry(mocker, strategy=strategy)
        executor = mocker.MagicMock()
        executor.run = mocker.AsyncMock(return_value=mocker.MagicMock(text=',d20'))
        mocker.patch(
            'bot.adapters.telegram.handler.AgentExecutor',
            return_value=executor,
        )

        user = User(id=DEFAULT_USER_ID, first_name='TestUser', is_bot=False)
        chat = Chat(id=DEFAULT_CHAT_ID, type=ChatType.GROUP)
        message = Message(
            message_id=1,
            date=datetime.now(tz=UTC),
            chat=chat,
            from_user=user,
            text='@resenhazord_bot oi',
            entities=(MessageEntity(type=MessageEntityType.MENTION, offset=0, length=16),),
        )
        await handler.handle(port, Update(update_id=1, message=message))

        executor.run.assert_called_once()
        port.send.assert_called()
