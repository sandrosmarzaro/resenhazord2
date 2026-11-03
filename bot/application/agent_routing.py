import re
from collections.abc import Iterable
from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

import structlog

from bot.application.command_registry import CommandRegistry
from bot.domain.constants import AGENT_MENU_HINT, BOT_MENTION_TAG, CLARIFY_PREFIX
from bot.domain.models.command_data import CommandData

if TYPE_CHECKING:
    from bot.application.throttled_agent import ThrottledAgent

logger = structlog.get_logger()


class AgentRouting:
    _SEND_ME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'\b(mande|me\s+manda|me\s+envie|envie)\s+(um?|uma)\b',
        re.IGNORECASE,
    )

    def __init__(
        self, registry: CommandRegistry, agent: ThrottledAgent, bot_jids: Iterable[str]
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._bot_numeric: frozenset[str] = frozenset(jid.split('@')[0] for jid in bot_jids if jid)

    def should_route(self, data: CommandData) -> bool:
        if self._is_explicit_mention(data):
            return True
        if data.is_group:
            return False
        # Private chat: a recognized ",command" takes the fast direct path;
        # natural language or an unmatched ",typo" goes to the agent to map or clarify.
        return self._registry.get_strategy(data.text) is None

    async def map(self, data: CommandData) -> CommandData | None:
        try:
            return await self._agent.run(data)
        except ValueError:
            logger.warning('agent_invalid_response', text=data.text)
            return replace(data, text=f'{CLARIFY_PREFIX}Erro inesperado. {AGENT_MENU_HINT}')

    def _is_explicit_mention(self, data: CommandData) -> bool:
        text_lower = (data.text or '').lower()
        for mentioned in data.mentioned_jids or ():
            if mentioned.split('@')[0] in self._bot_numeric:
                return True
        if BOT_MENTION_TAG in text_lower:
            return True
        return bool(self._SEND_ME_PATTERN.search(text_lower))
