import re
from dataclasses import replace
from typing import ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.constants import AGENT_MENU_HINT, CLARIFY_PREFIX, SUGGEST_PREFIX
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class CommandText:
    _BATCH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'\s+(\d+)x\s*$')
    _MAX_BATCH: ClassVar[int] = 5
    _BUILTIN_PREFIXES: ClassVar[tuple[str, ...]] = (CLARIFY_PREFIX, SUGGEST_PREFIX)

    @classmethod
    def split_batch(cls, data: CommandData) -> tuple[int, CommandData]:
        match = cls._BATCH_PATTERN.search(data.text)
        if not match:
            return 1, data
        count = min(int(match.group(1)), cls._MAX_BATCH)
        stripped_text = data.text[: match.start()]
        return max(count, 1), replace(data, text=stripped_text)

    @classmethod
    def builtin_reply(cls, data: CommandData) -> list[BotMessage] | None:
        text = data.text or ''
        for prefix in cls._BUILTIN_PREFIXES:
            if text.startswith(prefix):
                message = text[len(prefix) :].strip() or AGENT_MENU_HINT
                return [Reply.to(data).text(message)]
        return None
