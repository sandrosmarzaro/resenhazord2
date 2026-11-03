from typing import ClassVar

from bot.application.config_service import ConfigService
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandScope
from bot.domain.constants import COMMAND_OFF_IN_CHAT
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.dev_list import DevListService


class CommandGate:
    _DISABLED_MSG: ClassVar[str] = 'Esse comando está desativado. 🚫'
    _OFF_HERE_MSG: ClassVar[str] = COMMAND_OFF_IN_CHAT
    _DEV_ONLY_MSG: ClassVar[str] = 'Esse comando é apenas para desenvolvedores. 🛠️'

    def __init__(self, dev_list: DevListService, config: ConfigService) -> None:
        self._dev_list = dev_list
        self._config = config

    async def admit(
        self, command: Command, data: CommandData, repeat: int
    ) -> tuple[list[BotMessage] | None, int]:
        scope = command.config.scope
        if scope == CommandScope.DISABLED:
            return [Reply.to(data).text(self._DISABLED_MSG)], repeat

        is_dev = await self._dev_list.is_dev(data.sender_jid)
        if scope == CommandScope.DEV and not is_dev:
            return [Reply.to(data).text(self._DEV_ONLY_MSG)], repeat

        if not await self._config.is_enabled(data, command.config):
            return [Reply.to(data).text(self._OFF_HERE_MSG)], repeat

        if repeat > 1 and not is_dev:
            repeat = 1
        return None, repeat
