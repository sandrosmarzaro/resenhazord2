import logging
import re
import unicodedata
from collections.abc import Callable, Coroutine
from typing import Any, ClassVar

import sentry_sdk
import structlog
from telegram import BotCommand, Update
from telegram.error import InvalidToken, NetworkError, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.adapters.telegram.adapter import TelegramBotAdapter
from bot.adapters.telegram.agent_router import TelegramAgentRouter
from bot.adapters.telegram.handler import TelegramUpdateHandler
from bot.adapters.telegram.join_handler import TelegramJoinHandler
from bot.adapters.telegram.renderer import TelegramResponseRenderer
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandScope, Platform
from bot.infrastructure.platform_supervisor import PlatformAuthenticationError
from bot.ports.agent_orchestrator_port import AgentOrchestratorPort
from bot.ports.telegram_port import TelegramPort

_UPDATER_LOGGER = logging.getLogger('telegram.ext.Updater')

logger = structlog.get_logger()

TelegramCallback = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]
UpdateHandle = Callable[[TelegramPort, Update], Coroutine[Any, Any, None]]


class TelegramBot:
    NAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'[^a-z0-9_]')
    NAME_MAX_LENGTH: ClassVar[int] = 32
    DESCRIPTION_MAX_LENGTH: ClassVar[int] = 256
    MENU_SCOPES: ClassVar[frozenset[CommandScope]] = frozenset(
        {CommandScope.PUBLIC, CommandScope.ADMIN, CommandScope.NSFW}
    )
    START_COMMAND: ClassVar[str] = 'start'
    MENU_COMMAND: ClassVar[str] = 'menu'
    READ_TIMEOUT_SECONDS: ClassVar[float] = 60.0
    WRITE_TIMEOUT_SECONDS: ClassVar[float] = 60.0
    MEDIA_WRITE_TIMEOUT_SECONDS: ClassVar[float] = 120.0

    def __init__(
        self,
        token: str,
        bot_username: str,
        agent: AgentOrchestratorPort,
    ) -> None:
        self._app = (
            Application.builder()
            .token(token)
            .read_timeout(self.READ_TIMEOUT_SECONDS)
            .write_timeout(self.WRITE_TIMEOUT_SECONDS)
            .media_write_timeout(self.MEDIA_WRITE_TIMEOUT_SECONDS)
            .build()
        )
        router = TelegramAgentRouter(TelegramResponseRenderer(), agent)
        self._handler = TelegramUpdateHandler(bot_username, router)
        self._join_handler = TelegramJoinHandler()
        self._original_updater_level = _UPDATER_LOGGER.level

    async def start(self) -> None:
        self._app.add_error_handler(self._handle_error)
        _UPDATER_LOGGER.setLevel(logging.CRITICAL)
        self._register_handlers()
        try:
            await self._app.initialize()
        except InvalidToken as error:
            raise PlatformAuthenticationError(Platform.TELEGRAM) from error
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
        _UPDATER_LOGGER.setLevel(self._original_updater_level)
        logger.info('telegram_stopped')

    def _register_handlers(self) -> None:
        callback = self._make_callback(self._handler.handle)
        for command in CommandRegistry.instance().get_all():
            if not Platform.supports(command.config.platforms, Platform.TELEGRAM):
                continue
            self._add_command(command.config.name, callback)
            for alias in command.config.aliases:
                self._add_command(alias, callback)
            logger.info('telegram_command_registered', name=command.config.name)
        self._register_start_alias(callback)
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, callback))
        join_callback = self._make_callback(self._join_handler.handle)
        self._app.add_handler(ChatMemberHandler(join_callback, ChatMemberHandler.MY_CHAT_MEMBER))

    def _add_command(self, registry_name: str, callback: TelegramCallback) -> None:
        telegram_name = self._normalize_name(registry_name)
        self._handler.register_name(telegram_name, f',{registry_name}')
        self._app.add_handler(CommandHandler(telegram_name, callback))

    def _register_start_alias(self, callback: TelegramCallback) -> None:
        menu = CommandRegistry.instance().get_by_name(self.MENU_COMMAND)
        if menu is None or not Platform.supports(menu.config.platforms, Platform.TELEGRAM):
            return
        self._handler.register_name(self.START_COMMAND, f',{self.MENU_COMMAND}')
        self._app.add_handler(CommandHandler(self.START_COMMAND, callback))

    @staticmethod
    def _make_callback(handle: UpdateHandle) -> TelegramCallback:
        async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            await handle(TelegramBotAdapter(context.bot), update)

        return callback

    async def _handle_error(self, _update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        error = context.error
        if error is None:
            logger.warning('telegram_error_missing')
            return
        if isinstance(error, NetworkError | RetryAfter):
            logger.warning('telegram_transient_error', error=str(error))
            return
        logger.exception('telegram_unexpected_error', error=str(error))
        sentry_sdk.capture_exception(error)

    async def _publish_command_menu(self) -> None:
        # Aliases stay reachable by typing them; listing them would only repeat each command.
        commands = [
            BotCommand(
                command=self._normalize_name(command.config.name),
                description=command.menu_description[: self.DESCRIPTION_MAX_LENGTH],
            )
            for command in CommandRegistry.instance().get_all()
            if self._is_menu_eligible(command)
        ]
        try:
            await self._app.bot.set_my_commands(commands)
        except TelegramError as error:
            logger.warning('telegram_set_commands_failed', error=str(error))

    @classmethod
    def _is_menu_eligible(cls, command: Command) -> bool:
        return (
            Platform.supports(command.config.platforms, Platform.TELEGRAM)
            and command.config.scope in cls.MENU_SCOPES
        )

    @classmethod
    def _normalize_name(cls, name: str) -> str:
        decomposed = unicodedata.normalize('NFD', name.lower())
        ascii_only = ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')
        cleaned = cls.NAME_PATTERN.sub('', ascii_only.replace(' ', '_').replace('-', '_'))
        return cleaned[: cls.NAME_MAX_LENGTH]
