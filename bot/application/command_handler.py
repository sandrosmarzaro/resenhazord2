import structlog

from bot.application.command_registry import CommandRegistry
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()


class CommandHandler:
    def __init__(self, registry: CommandRegistry | None = None) -> None:
        self._registry = registry or CommandRegistry.instance()

    async def handle(self, data: CommandData) -> list[BotMessage] | None:
        """Returns messages if a command matched, None if no match."""
        command = self._registry.get_strategy(data.text)
        if command is None:
            return None

        logger.info('executing_command', command=command.config.name, jid=data.jid)

        try:
            return await command.run(data)
        except BotError:
            raise
        except Exception:
            logger.exception('command_execution_failed', command=command.config.name)
            raise
