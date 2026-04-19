from typing import ClassVar

import structlog
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.constants import ChatType, MessageEntityType

from bot.adapters.telegram.renderer import TelegramResponseRenderer
from bot.adapters.telegram.typing_loop import keep_typing
from bot.application.command_registry import CommandRegistry
from bot.application.message_preprocess import preprocess_for_telegram
from bot.domain.commands.base import Command, CommandScope, Platform
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.ports.telegram_port import TelegramKind, TelegramOutbound, TelegramPort

logger = structlog.get_logger()


class TelegramUpdateHandler:
    COMMAND_PREFIX: ClassVar[str] = ','
    GROUP_CHAT_TYPES: ClassVar[frozenset[str]] = frozenset({ChatType.GROUP, ChatType.SUPERGROUP})
    UNKNOWN_COMMAND_MESSAGE: ClassVar[str] = 'Comando nao reconhecido.'
    GROUP_ONLY_MESSAGE: ClassVar[str] = 'Esse comando so funciona em grupos.'
    NSFW_ONLY_MESSAGE: ClassVar[str] = 'Este comando so pode ser usado em canais NSFW.'
    GENERIC_ERROR_MESSAGE: ClassVar[str] = 'Ocorreu um erro ao executar o comando.'
    EMPTY_REPLY_MESSAGE: ClassVar[str] = 'Sem resposta do bot.'
    ACK_REACTION: ClassVar[str] = '\U0001f44d'

    def __init__(
        self,
        bot_username: str,
        nsfw_chat_ids: frozenset[int],
        renderer: TelegramResponseRenderer | None = None,
    ) -> None:
        self._bot_username = bot_username.lower()
        self._nsfw_chat_ids = nsfw_chat_ids
        self._renderer = renderer or TelegramResponseRenderer()
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
            return

        text = self._build_command_text(command_name, message)
        strategy = CommandRegistry.instance().get_strategy(text)
        if strategy is None:
            await self._reply_text(port, chat.id, self.UNKNOWN_COMMAND_MESSAGE)
            return

        if strategy.config.group_only and chat.type not in self.GROUP_CHAT_TYPES:
            await self._reply_text(port, chat.id, self.GROUP_ONLY_MESSAGE)
            return

        if strategy.config.scope == CommandScope.NSFW and chat.id not in self._nsfw_chat_ids:
            await self._reply_text(port, chat.id, self.NSFW_ONLY_MESSAGE)
            return

        data = self._build_command_data(message, chat, user, text)
        await self._safe_react(port, chat.id, message.message_id)
        async with keep_typing(port, chat.id):
            await self._run_and_reply(port, strategy, data, chat.id, command_name)

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

    async def _run_and_reply(
        self,
        port: TelegramPort,
        strategy: Command,
        data: CommandData,
        chat_id: int,
        command_name: str,
    ) -> None:
        try:
            messages = await strategy.run(data)
        except BotError as error:
            await self._reply_text(port, chat_id, error.user_message)
            return
        except Exception:
            logger.exception('telegram_command_error', command=command_name)
            await self._reply_text(port, chat_id, self.GENERIC_ERROR_MESSAGE)
            return

        if not messages:
            await self._reply_text(port, chat_id, self.EMPTY_REPLY_MESSAGE)
            return

        messages = await preprocess_for_telegram(messages)
        for outbound in self._renderer.render_many(messages, chat_id):
            await port.send(outbound)

    @staticmethod
    async def _reply_text(port: TelegramPort, chat_id: int, text: str) -> None:
        await port.send(TelegramOutbound(kind=TelegramKind.TEXT, chat_id=chat_id, text=text))

    @classmethod
    async def _safe_react(cls, port: TelegramPort, chat_id: int, message_id: int) -> None:
        try:
            await port.react(chat_id, message_id, cls.ACK_REACTION)
        except Exception:
            logger.exception('telegram_react_failed', chat_id=chat_id, message_id=message_id)
