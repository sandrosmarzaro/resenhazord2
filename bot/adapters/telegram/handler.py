from typing import ClassVar

import structlog
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.constants import ChatType, MessageEntityType

from bot.adapters.telegram.agent_router import TelegramAgentRouter
from bot.adapters.telegram.renderer import TelegramResponseRenderer
from bot.adapters.telegram.typing_loop import TypingLoop
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandScope, Platform
from bot.domain.models.command_data import CommandData
from bot.ports.telegram_port import TelegramKind, TelegramOutbound, TelegramPort

logger = structlog.get_logger()


class TelegramUpdateHandler:
    COMMAND_PREFIX: ClassVar[str] = ','
    GROUP_CHAT_TYPES: ClassVar[frozenset[str]] = frozenset({ChatType.GROUP, ChatType.SUPERGROUP})
    UNKNOWN_COMMAND_MESSAGE: ClassVar[str] = 'Comando nao reconhecido.'
    GROUP_ONLY_MESSAGE: ClassVar[str] = 'Esse comando so funciona em grupos.'
    NSFW_ONLY_MESSAGE: ClassVar[str] = 'Este comando so pode ser usado em canais NSFW.'

    def __init__(
        self,
        bot_username: str,
        nsfw_chat_ids: frozenset[int],
        renderer: TelegramResponseRenderer | None = None,
    ) -> None:
        self._bot_username = bot_username.lower()
        self._nsfw_chat_ids = nsfw_chat_ids
        self._renderer = renderer or TelegramResponseRenderer()
        self._router = TelegramAgentRouter(self._renderer)
        self._name_map: dict[str, str] = {}

    def register_name(self, telegram_name: str, registry_text: str) -> None:
        self._name_map[telegram_name] = registry_text

    async def handle(self, port: TelegramPort, update: Update) -> None:
        message = update.effective_message
        chat = update.effective_chat
        user = update.effective_user
        if message is None or chat is None or user is None or message.text is None:
            return

        command_name = self._extract_command_name(message)
        if command_name is None:
            await self._maybe_route_agent(port, message, chat, user)
            return

        text = self._build_command_text(command_name, message)
        strategy = CommandRegistry.instance().get_strategy(text)
        if strategy is None:
            await self._reply_text(port, chat.id, self.UNKNOWN_COMMAND_MESSAGE)
            return

        block = self._strategy_block_message(strategy, chat)
        if block is not None:
            await self._reply_text(port, chat.id, block)
            return

        data = self._build_command_data(message, chat, user, text)
        await TelegramAgentRouter.safe_react(port, chat.id, message.message_id)
        async with TypingLoop.keep_typing(port, chat.id):
            await self._router.run_and_reply(port, strategy, data, chat.id, command_name)

    async def _maybe_route_agent(
        self,
        port: TelegramPort,
        message: Message,
        chat: Chat,
        user: User,
    ) -> None:
        is_dm = chat.type == ChatType.PRIVATE
        if not (is_dm or TelegramAgentRouter.is_agent_mention(message, self._bot_username)):
            return
        data = self._build_command_data(message, chat, user, message.text or '')
        await self._router.route(port, message, chat, data)

    def _strategy_block_message(self, strategy: Command, chat: Chat) -> str | None:
        if strategy.config.group_only and chat.type not in self.GROUP_CHAT_TYPES:
            return self.GROUP_ONLY_MESSAGE
        if strategy.config.scope == CommandScope.NSFW and chat.id not in self._nsfw_chat_ids:
            return self.NSFW_ONLY_MESSAGE
        return None

    def _extract_command_name(self, message: Message) -> str | None:
        entity = self._find_command_entity(message.entities)
        if entity is None or message.text is None:
            return None
        token = message.text[entity.offset : entity.offset + entity.length].lstrip('/')
        return self._strip_bot_mention(token)

    @staticmethod
    def _find_command_entity(entities: tuple[MessageEntity, ...]) -> MessageEntity | None:
        for entity in entities:
            if entity.type == MessageEntityType.BOT_COMMAND and entity.offset == 0:
                return entity
        return None

    def _strip_bot_mention(self, token: str) -> str:
        if '@' not in token:
            return token
        name, mention = token.split('@', 1)
        if self._bot_username and mention.lower() != self._bot_username:
            return token
        return name

    def _build_command_text(self, command_name: str, message: Message) -> str:
        base = self._name_map.get(command_name, f'{self.COMMAND_PREFIX}{command_name}')
        entity = self._find_command_entity(message.entities)
        rest = ''
        if entity is not None and message.text is not None:
            rest = message.text[entity.offset + entity.length :].strip()
        return f'{base} {rest}'.strip()

    @classmethod
    def _build_command_data(
        cls, message: Message, chat: Chat, user: User, text: str
    ) -> CommandData:
        return CommandData(
            text=text,
            jid=str(chat.id),
            sender_jid=str(user.id),
            message_id=str(message.message_id),
            is_group=chat.type in cls.GROUP_CHAT_TYPES,
            push_name=user.full_name,
            platform=Platform.TELEGRAM,
        )

    @staticmethod
    async def _reply_text(port: TelegramPort, chat_id: int, text: str) -> None:
        await port.send(TelegramOutbound(kind=TelegramKind.TEXT, chat_id=chat_id, text=text))
