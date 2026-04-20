import re
import unicodedata
from collections.abc import Callable, Coroutine
from typing import Any, ClassVar

import structlog
from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.adapters.telegram.adapter import TelegramBotAdapter
from bot.adapters.telegram.handler import TelegramUpdateHandler
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandScope, Platform

logger = structlog.get_logger()

TelegramCallback = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]


class TelegramBot:
    NAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'[^a-z0-9_]')
    NAME_MAX_LENGTH: ClassVar[int] = 32
    DESCRIPTION_MAX_LENGTH: ClassVar[int] = 256
    PUBLIC_SCOPE: ClassVar[CommandScope] = CommandScope.PUBLIC
    NSFW_SCOPE: ClassVar[CommandScope] = CommandScope.NSFW
    START_COMMAND: ClassVar[str] = 'start'
    MENU_COMMAND: ClassVar[str] = 'menu'
    READ_TIMEOUT_SECONDS: ClassVar[float] = 60.0
    WRITE_TIMEOUT_SECONDS: ClassVar[float] = 60.0
    MEDIA_WRITE_TIMEOUT_SECONDS: ClassVar[float] = 120.0

    def __init__(self, token: str, bot_username: str, nsfw_chat_ids: frozenset[int]) -> None:
        self._app = (
            Application.builder()
            .token(token)
            .read_timeout(self.READ_TIMEOUT_SECONDS)
            .write_timeout(self.WRITE_TIMEOUT_SECONDS)
            .media_write_timeout(self.MEDIA_WRITE_TIMEOUT_SECONDS)
            .build()
        )
        self._handler = TelegramUpdateHandler(bot_username, nsfw_chat_ids)
        self._nsfw_chat_ids = nsfw_chat_ids

    async def start(self) -> None:
        self._register_handlers()
        await self._app.initialize()
        await self._app.start()
        if self._app.updater is not None:
            await self._app.updater.start_polling()
        await self._publish_command_menu()
        logger.info('telegram_connected')

    async def stop(self) -> None:
        if self._app.updater is not None:
            await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()
        logger.info('telegram_stopped')

    def _register_handlers(self) -> None:
        callback = self._make_callback()
        for command in CommandRegistry.instance().get_all():
            if Platform.TELEGRAM not in command.config.platforms:
                continue
            self._add_command(command.config.name, callback)
            for alias in command.config.aliases:
                self._add_command(alias, callback)
            logger.info('telegram_command_registered', name=command.config.name)
        self._register_start_alias(callback)

    def _add_command(self, registry_name: str, callback: TelegramCallback) -> None:
        telegram_name = self._normalize_name(registry_name)
        self._handler.register_name(telegram_name, f',{registry_name}')
        self._app.add_handler(CommandHandler(telegram_name, callback))

    def _register_start_alias(self, callback: TelegramCallback) -> None:
        menu = CommandRegistry.instance().get_by_name(self.MENU_COMMAND)
        if menu is None or Platform.TELEGRAM not in menu.config.platforms:
            return
        self._handler.register_name(self.START_COMMAND, f',{self.MENU_COMMAND}')
        self._app.add_handler(CommandHandler(self.START_COMMAND, callback))

    def _make_callback(self) -> TelegramCallback:
        handler = self._handler

        async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            port = TelegramBotAdapter(context.bot)
            await handler.handle(port, update)

        return callback

    async def _publish_command_menu(self) -> None:
        public = self._bot_commands_for_scopes({self.PUBLIC_SCOPE})
        await self._safe_set_commands(public)
        if not self._nsfw_chat_ids:
            return
        nsfw = self._bot_commands_for_scopes({self.PUBLIC_SCOPE, self.NSFW_SCOPE})
        for chat_id in self._nsfw_chat_ids:
            await self._safe_set_commands(nsfw, scope=BotCommandScopeChat(chat_id=chat_id))

    async def _safe_set_commands(
        self, commands: list[BotCommand], scope: BotCommandScopeChat | None = None
    ) -> None:
        try:
            if scope is None:
                await self._app.bot.set_my_commands(commands)
            else:
                await self._app.bot.set_my_commands(commands, scope=scope)
        except TelegramError as error:
            logger.warning('telegram_set_commands_failed', scope=repr(scope), error=str(error))

    def _bot_commands_for_scopes(self, scopes: set[CommandScope]) -> list[BotCommand]:
        commands: list[BotCommand] = []
        seen: set[str] = set()
        for cmd in CommandRegistry.instance().get_all():
            if not self._is_menu_eligible(cmd, scopes):
                continue
            description = cmd.menu_description[: self.DESCRIPTION_MAX_LENGTH]
            for name in (cmd.config.name, *cmd.config.aliases):
                telegram_name = self._normalize_name(name)
                if not telegram_name or telegram_name in seen:
                    continue
                seen.add(telegram_name)
                commands.append(BotCommand(command=telegram_name, description=description))
        return commands

    @staticmethod
    def _is_menu_eligible(command: Command, scopes: set[CommandScope]) -> bool:
        return Platform.TELEGRAM in command.config.platforms and command.config.scope in scopes

    @classmethod
    def _normalize_name(cls, name: str) -> str:
        decomposed = unicodedata.normalize('NFD', name.lower())
        ascii_only = ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')
        cleaned = cls.NAME_PATTERN.sub('', ascii_only.replace(' ', '_').replace('-', '_'))
        return cleaned[: cls.NAME_MAX_LENGTH]
