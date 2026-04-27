from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.constants import ChatType, MessageEntityType

from bot.adapters.telegram.handler import TelegramUpdateHandler
from bot.adapters.telegram.renderer import TelegramResponseRenderer
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    CommandScope,
    Platform,
)
from bot.domain.models.message import BotMessage

if TYPE_CHECKING:
    from bot.domain.models.command_data import CommandData

CHAT_ID = 1234

DEFAULT_CHAT_ID = 111222333
DEFAULT_USER_ID = 999888777
DEFAULT_BOT_USERNAME = 'resenhazord_bot'


@pytest.fixture
def port(mocker):
    mock_port = mocker.AsyncMock()
    mock_port.send = mocker.AsyncMock()
    mock_port.send_typing = mocker.AsyncMock()
    mock_port.react = mocker.AsyncMock()
    return mock_port


@pytest.fixture
def handler() -> TelegramUpdateHandler:
    return TelegramUpdateHandler(
        bot_username=DEFAULT_BOT_USERNAME,
        nsfw_chat_ids=frozenset({99}),
    )


@pytest.fixture
def renderer() -> TelegramResponseRenderer:
    return TelegramResponseRenderer()


def render(renderer: TelegramResponseRenderer, content):
    return renderer.render(BotMessage(jid='jid', content=content), CHAT_ID)


def make_update(
    text: str,
    *,
    chat_type: str = ChatType.PRIVATE,
    chat_id: int = DEFAULT_CHAT_ID,
    entities: tuple[MessageEntity, ...] | None = None,
) -> Update:
    user = User(id=DEFAULT_USER_ID, first_name='TestUser', is_bot=False)
    chat = Chat(id=chat_id, type=chat_type)
    if entities is None:
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


def make_mention_update(
    text: str, mention_length: int, *, chat_type: str = ChatType.GROUP
) -> Update:
    return make_update(
        text,
        chat_type=chat_type,
        entities=(MessageEntity(type=MessageEntityType.MENTION, offset=0, length=mention_length),),
    )


def make_strategy(
    mocker,
    messages: list | None = None,
    *,
    group_only: bool = False,
    scope: CommandScope = CommandScope.PUBLIC,
):
    strategy = mocker.MagicMock()
    strategy.run = mocker.AsyncMock(return_value=messages or [])
    strategy.config = mocker.MagicMock(group_only=group_only, scope=scope)
    return strategy


def patch_registry(mocker, *, strategy=None, by_name=None):
    registry = mocker.MagicMock()
    registry.get_strategy.return_value = strategy
    registry.get_by_name.return_value = by_name
    mocker.patch(
        'bot.adapters.telegram.handler.CommandRegistry.instance',
        return_value=registry,
    )
    return registry


def stub_agent_executor(mocker, *, returns_text: str):
    executor = mocker.MagicMock()
    executor.run = mocker.AsyncMock(return_value=mocker.MagicMock(text=returns_text))
    mocker.patch(
        'bot.adapters.telegram.agent_router.AgentExecutor',
        return_value=executor,
    )
    return executor


class FakeCommand(Command):
    def __init__(
        self,
        name: str,
        *,
        platforms: list[Platform],
        scope: CommandScope = CommandScope.PUBLIC,
        description: str = 'desc',
        aliases: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._name = name
        self._platforms = platforms
        self._scope = scope
        self._description = description
        self._aliases = aliases or []

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name=self._name,
            category=Category.OTHER,
            platforms=self._platforms,
            scope=self._scope,
            aliases=list(self._aliases),
        )

    @property
    def menu_description(self) -> str:
        return self._description

    async def execute(self, data: CommandData, parsed) -> list[BotMessage]:
        return []
