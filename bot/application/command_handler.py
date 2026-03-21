import structlog
import structlog.contextvars

from bot.application.command_registry import CommandRegistry
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandScope
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.dev_list import DevListService

logger = structlog.get_logger()

DISABLED_MSG = 'Esse comando está desativado. 🚫'
DEV_ONLY_MSG = 'Esse comando é apenas para desenvolvedores. 🛠️'


class CommandHandler:
    def __init__(
        self,
        registry: CommandRegistry | None = None,
        dev_list: DevListService | None = None,
    ) -> None:
        self._registry = registry or CommandRegistry.instance()
        self._dev_list = dev_list or DevListService()

    async def handle(self, data: CommandData) -> list[BotMessage] | None:
        """Returns messages if a command matched, None if no match."""
        command = self._registry.get_strategy(data.text)
        if command is None:
            return None

        structlog.contextvars.bind_contextvars(command=command.config.name)

        scope = command.config.scope
        if scope == CommandScope.DISABLED:
            return [Reply.to(data).text(DISABLED_MSG)]
        if scope == CommandScope.DEV and not await self._dev_list.is_dev(data.sender_jid):
            return [Reply.to(data).text(DEV_ONLY_MSG)]

        logger.info('executing_command')

        try:
            return await command.run(data)
        except BotError:
            raise
        except Exception:
            logger.exception('command_execution_failed')
            raise
