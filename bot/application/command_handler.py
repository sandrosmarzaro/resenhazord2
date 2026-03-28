import re
from collections.abc import Awaitable, Callable
from dataclasses import replace

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
BATCH_PATTERN = re.compile(r'\s+(\d+)x\s*$')
MAX_BATCH = 5


class CommandHandler:
    def __init__(
        self,
        registry: CommandRegistry | None = None,
        dev_list: DevListService | None = None,
    ) -> None:
        self._registry = registry or CommandRegistry.instance()
        self._dev_list = dev_list or DevListService()

    async def handle(
        self,
        data: CommandData,
        *,
        on_match: Callable[[], Awaitable[None]] | None = None,
    ) -> list[BotMessage] | None:
        """Returns messages if a command matched, None if no match."""
        logger.info('handle_raw', text=repr(data.text))
        repeat, data = self._parse_batch(data)
        logger.info('handle_parsed', repeat=repeat, text=repr(data.text))

        command = self._registry.get_strategy(data.text)
        if command is None:
            return None

        structlog.contextvars.bind_contextvars(command=command.config.name)

        if on_match:
            await on_match()

        scope = command.config.scope
        if scope == CommandScope.DISABLED:
            return [Reply.to(data).text(DISABLED_MSG)]

        is_dev = await self._dev_list.is_dev(data.sender_jid)
        if scope == CommandScope.DEV and not is_dev:
            return [Reply.to(data).text(DEV_ONLY_MSG)]
        if repeat > 1 and not is_dev:
            repeat = 1

        logger.info('executing_command', batch=repeat if repeat > 1 else None)

        try:
            messages: list[BotMessage] = []
            for _ in range(repeat):
                messages.extend(await command.run(data))
        except BotError:
            raise
        except Exception:
            logger.exception('command_execution_failed')
            raise
        else:
            return messages

    @staticmethod
    def _parse_batch(data: CommandData) -> tuple[int, CommandData]:
        match = BATCH_PATTERN.search(data.text)
        if not match:
            return 1, data
        count = min(int(match.group(1)), MAX_BATCH)
        stripped_text = data.text[: match.start()]
        return max(count, 1), replace(data, text=stripped_text)
