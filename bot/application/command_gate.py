from typing import ClassVar

from bot.application.config_service import ConfigService
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandScope, Platform
from bot.domain.constants import COMMAND_OFF_IN_CHAT
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.dev_list import DevListService
from bot.infrastructure.metrics import record_rejection


class CommandGate:
    _MESSAGES: ClassVar[dict[str, str]] = {
        'disabled': 'Esse comando está desativado. 🚫',
        'dev_only': 'Esse comando é apenas para desenvolvedores. 🛠️',
        'off_here': COMMAND_OFF_IN_CHAT,
    }
    _NAMESPACED_PLATFORMS: ClassVar[frozenset[Platform]] = frozenset(
        {Platform.DISCORD, Platform.TELEGRAM}
    )

    def __init__(self, dev_list: DevListService, config: ConfigService) -> None:
        self._dev_list = dev_list
        self._config = config

    async def admit(
        self, command: Command, data: CommandData, repeat: int
    ) -> tuple[list[BotMessage] | None, int]:
        is_dev = await self._is_dev(command, data, repeat)
        if rejection := await self._rejection(command, data, is_dev=is_dev):
            return [Reply.to(data).text(rejection)], repeat
        if repeat > 1 and not is_dev:
            repeat = 1
        return None, repeat

    async def rejection_text(self, command: Command, data: CommandData) -> str | None:
        is_dev = await self._is_dev(command, data, 1)
        return await self._rejection(command, data, is_dev=is_dev)

    async def _rejection(self, command: Command, data: CommandData, *, is_dev: bool) -> str | None:
        reason = await self._reason(command, data, is_dev=is_dev)
        if reason is None:
            return None
        record_rejection(reason, command.config.name, command.config.scope)
        return self._MESSAGES[reason]

    async def _reason(self, command: Command, data: CommandData, *, is_dev: bool) -> str | None:
        scope = command.config.scope
        if scope == CommandScope.DISABLED:
            return 'disabled'
        if scope == CommandScope.DEV and not is_dev:
            return 'dev_only'
        if not await self._config.is_enabled(data, command.config):
            return 'off_here'
        return None

    async def _is_dev(self, command: Command, data: CommandData, repeat: int) -> bool:
        # Only a dev command or a batch needs the lookup, so most commands skip a Mongo
        # round trip.
        if command.config.scope != CommandScope.DEV and repeat == 1:
            return False
        return await self._dev_list.is_dev(self._dev_key(data))

    @classmethod
    def _dev_key(cls, data: CommandData) -> str:
        # Discord and Telegram send the bare user id. Namespaced, it can't be read as a
        # WhatsApp number or LID, and it matches the discord:<id> that ,dev add stores.
        if data.platform in cls._NAMESPACED_PLATFORMS:
            return f'{data.platform}:{data.sender_jid}'
        return data.sender_jid
