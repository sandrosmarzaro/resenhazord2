"""Compiles a CommandConfig into the regex used for matching command text."""

import re
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from bot.domain.commands.base import CommandConfig


class CommandParserRegex:
    METACHARS: ClassVar[re.Pattern[str]] = re.compile(r'[.*+?^${}()|[\]\\]')
    NON_ASCII: ClassVar[re.Pattern[str]] = re.compile(r'[^\x00-\x7f]')
    INTERNAL_WHITESPACE: ClassVar[re.Pattern[str]] = re.compile(r'\s+')

    @classmethod
    def build(cls, config: 'CommandConfig') -> re.Pattern[str]:
        parts: list[str] = [r'^\s*,\s*', cls.name_alternation(config)]
        token_alt = cls._token_alternation(config)
        if token_alt:
            parts.append(f'(?:\\s+(?:{token_alt}))*')
        parts.append(cls._args_segment(config))
        return re.compile(''.join(parts), re.IGNORECASE)

    @classmethod
    def name_alternation(cls, config: 'CommandConfig') -> str:
        patterns = [cls.name_pattern(name) for name in cls.sorted_names(config)]
        if len(patterns) == 1:
            return patterns[0]
        return f'(?:{"|".join(patterns)})'

    @staticmethod
    def sorted_names(config: 'CommandConfig') -> list[str]:
        return sorted([config.name, *config.aliases], key=len, reverse=True)

    @classmethod
    def name_pattern(cls, name: str) -> str:
        return cls.INTERNAL_WHITESPACE.sub(r'\\s*', cls.escape(name))

    @classmethod
    def escape(cls, text: str) -> str:
        escaped = cls.METACHARS.sub(r'\\\g<0>', text)
        return cls.NON_ASCII.sub('.', escaped)

    @classmethod
    def _token_alternation(cls, config: 'CommandConfig') -> str:
        alternatives: list[str] = []
        for opt in config.options:
            if opt.values:
                values = sorted(opt.values, key=len, reverse=True)
                alternatives.append(f'(?:{"|".join(cls.escape(v) for v in values)})')
            elif opt.pattern:
                alternatives.append(f'(?:{opt.pattern})')
        alternatives.extend(cls.escape(flag) for flag in config.flags)
        return '|'.join(alternatives)

    @classmethod
    def _args_segment(cls, config: 'CommandConfig') -> str:
        from bot.domain.commands.base import ArgType

        if config.args == ArgType.NONE:
            return r'\s*$'
        if config.args_pattern:
            stripped = cls._strip_anchors(config.args_pattern)
            return f'\\s*{stripped}\\s*$'
        if config.args == ArgType.REQUIRED:
            return r'\s+.+'
        return r'(?:\s+.*)?$'

    @staticmethod
    def _strip_anchors(pattern: str) -> str:
        return pattern.removeprefix('^').removesuffix('$')
