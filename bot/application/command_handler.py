import re
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import ClassVar

import httpx
import structlog

from bot.application.agent_executor import AgentExecutor
from bot.application.command_registry import CommandRegistry
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandScope
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.dev_list import DevListService
from bot.settings import Settings

logger = structlog.get_logger()


class CommandHandler:
    _DISABLED_MSG: ClassVar[str] = 'Esse comando está desativado. 🚫'
    _DEV_ONLY_MSG: ClassVar[str] = 'Esse comando é apenas para desenvolvedores. 🛠️'
    _BATCH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'\s+(\d+)x\s*$')
    _MAX_BATCH: ClassVar[int] = 5
    _SEND_ME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'\b(mande|me\s+manda|me\s+envie|envie)\s+(um?|uma)\b',
        re.IGNORECASE,
    )

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        dev_list: DevListService | None = None,
    ) -> None:
        self._registry = registry or CommandRegistry.instance()
        self._dev_list = dev_list or DevListService()
        self._agent_executor: AgentExecutor | None = None
        settings = Settings()
        self._bot_numeric: frozenset[str] = frozenset(
            jid.split('@')[0]
            for jid in (
                settings.resenhazord2_jid,
                settings.resenha_jid,
                settings.resenhazord2_lid,
            )
            if jid
        )

    def _is_agent_mention(self, data: CommandData) -> bool:
        """Check if message is agent-mode: @resenhazord mention, DM, or 'send me a...' pattern."""
        text_lower = (data.text or '').lower()
        for mentioned in data.mentioned_jids or ():
            if mentioned.split('@')[0] in self._bot_numeric:
                return True
        if AgentExecutor.BOT_MENTION_TAG in text_lower:
            return True
        if not data.is_group:
            return True
        return bool(self._SEND_ME_PATTERN.search(text_lower))

    async def _run_agent(self, data: CommandData) -> CommandData:
        """Run the LLM agent to map natural language to command."""
        try:
            if self._agent_executor is None:
                self._agent_executor = AgentExecutor(self._registry)
            return await self._agent_executor.run(data)
        except (httpx.HTTPError, RuntimeError, ValueError):
            logger.warning('agent_execution_failed', text=data.text)
            return data

    # C901 suppressed: dispatch fan-out (registry match, agent path, DM
    # fallback, ack callback, cooldown branch) — splitting scatters branches.
    async def handle(  # noqa: C901
        self,
        data: CommandData,
        *,
        on_match: Callable[[], Awaitable[None]] | None = None,
    ) -> list[BotMessage] | None:
        """Returns messages if a command matched, None if no match."""
        logger.debug('handle_raw', text=repr(data.text))

        is_agent = self._is_agent_mention(data)
        if is_agent:
            logger.info('agent_mention_detected', text=data.text)
            data = await self._run_agent(data)

        repeat, data = self._parse_batch(data)
        logger.debug('handle_parsed', repeat=repeat, text=repr(data.text))

        if builtin := self._parse_builtin_prefix(data):
            return builtin

        command = self._registry.get_strategy(data.text)
        logger.debug(
            'command_strategy_found',
            command=command.config.name if command else None,
            text=data.text,
        )
        if command is None:
            # Agent mode returns None (no response); regular mode returns None (no command matched)
            # Future: agent fallback could differ (e.g., "command not found" message)
            return None

        if on_match:
            await on_match()

        scope = command.config.scope
        if scope == CommandScope.DISABLED:
            return [Reply.to(data).text(self._DISABLED_MSG)]

        is_dev = await self._dev_list.is_dev(data.sender_jid)
        if scope == CommandScope.DEV and not is_dev:
            return [Reply.to(data).text(self._DEV_ONLY_MSG)]
        if repeat > 1 and not is_dev:
            repeat = 1

        logger.debug('executing_command', batch=repeat if repeat > 1 else None)

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

    @classmethod
    def _parse_batch(cls, data: CommandData) -> tuple[int, CommandData]:
        match = cls._BATCH_PATTERN.search(data.text)
        if not match:
            return 1, data
        count = min(int(match.group(1)), cls._MAX_BATCH)
        stripped_text = data.text[: match.start()]
        return max(count, 1), replace(data, text=stripped_text)

    def _parse_builtin_prefix(self, data: CommandData) -> list[BotMessage] | None:
        """Parse ,clarify: and ,suggest: prefixes."""
        text = data.text or ''
        if text.startswith(',clarify:'):
            question = text[len(',clarify:') :].strip()
            return [Reply.to(data).text(question)]
        if text.startswith(',suggest:'):
            suggestion = text[len(',suggest:') :].strip()
            return [Reply.to(data).text(suggestion)]
        return None
