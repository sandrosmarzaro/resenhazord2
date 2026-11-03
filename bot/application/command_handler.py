from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import structlog

from bot.application.agent_routing import AgentRouting
from bot.application.command_gate import CommandGate
from bot.application.command_registry import CommandRegistry
from bot.application.command_text import CommandText
from bot.application.config_service import ConfigService
from bot.domain.commands.base import Command
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.dev_list import DevListService
from bot.infrastructure.cached_config_store import CachedConfigStore
from bot.settings import Settings

if TYPE_CHECKING:
    from bot.application.throttled_agent import ThrottledAgent

logger = structlog.get_logger()


class CommandHandler:
    def __init__(
        self,
        registry: CommandRegistry,
        agent: ThrottledAgent,
        dev_list: DevListService | None = None,
        config_service: ConfigService | None = None,
    ) -> None:
        self._registry = registry
        self._gate = CommandGate(
            dev_list or DevListService(),
            config_service or ConfigService(CachedConfigStore.instance()),
        )
        settings = Settings()
        self._agent_routing = AgentRouting(
            registry,
            agent,
            (settings.resenhazord2_jid, settings.resenha_jid, settings.resenhazord2_lid),
        )

    async def handle(
        self,
        data: CommandData,
        *,
        on_match: Callable[[Command], Awaitable[None]] | None = None,
    ) -> list[BotMessage] | None:
        logger.debug('handle_raw', text=repr(data.text))

        if self._agent_routing.should_route(data):
            logger.info('agent_routing', text=data.text)
            mapped = await self._agent_routing.map(data)
            if mapped is None:
                return None
            data = mapped

        repeat, data = CommandText.split_batch(data)
        logger.debug('handle_parsed', repeat=repeat, text=repr(data.text))

        if builtin := CommandText.builtin_reply(data):
            return builtin

        command = self._registry.get_strategy(data.text)
        logger.debug(
            'command_strategy_found',
            command=command.config.name if command else None,
            text=data.text,
        )
        if command is None:
            return None

        return await self._dispatch(command, data, repeat, on_match)

    async def _dispatch(
        self,
        command: Command,
        data: CommandData,
        repeat: int,
        on_match: Callable[[Command], Awaitable[None]] | None,
    ) -> list[BotMessage] | None:
        rejection, repeat = await self._gate.admit(command, data, repeat)
        if rejection:
            return rejection

        # Only a command that will run reaches the hook, so a rejected ,dl never waits
        # for the consumer's exclusive lane.
        if on_match:
            await on_match(command)

        logger.debug('executing_command', batch=repeat if repeat > 1 else None)
        return await self._run_command(command, data, repeat)

    @staticmethod
    async def _run_command(
        command: Command,
        data: CommandData,
        repeat: int,
    ) -> list[BotMessage]:
        try:
            messages: list[BotMessage] = []
            for _ in range(repeat):
                messages.extend(await command.run(data))
        except BotError:
            raise
        except Exception:
            logger.exception('command_execution_failed')
            raise
        return messages
