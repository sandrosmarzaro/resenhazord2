"""Builds a regex from CommandConfig for matching, and tokenizes text for parsing."""

import re
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from bot.domain.commands.base import CommandConfig, OptionDef, ParsedCommand


class CommandParser:
    LEADING_COMMA: ClassVar[re.Pattern[str]] = re.compile(r'^\s*,\s*')
    METACHARS: ClassVar[re.Pattern[str]] = re.compile(r'[.*+?^${}()|[\]\\]')
    NON_ASCII: ClassVar[re.Pattern[str]] = re.compile(r'[^\x00-\x7f]')
    INTERNAL_WHITESPACE: ClassVar[re.Pattern[str]] = re.compile(r'\s+')

    def __init__(self, config: 'CommandConfig') -> None:
        self._config = config
        self._regex = self._build_regex()

    def matches(self, text: str) -> bool:
        return self._regex.search(text) is not None

    def parse(self, text: str) -> 'ParsedCommand':
        from bot.domain.commands.base import ParsedCommand

        remaining = self.LEADING_COMMA.sub('', text)
        command_name, remaining = self._consume_command_name(remaining)

        flags: set[str] = set()
        options: dict[str, str] = {}
        rest_parts: list[str] = []

        tokens = [t for t in remaining.split() if t]
        index = 0
        while index < len(tokens):
            index = self._consume_token(tokens, index, options, flags, rest_parts)

        return ParsedCommand(
            command_name=command_name,
            flags=flags,
            options=options,
            rest=' '.join(rest_parts),
        )

    def _consume_command_name(self, text: str) -> tuple[str, str]:
        for name in self._sorted_names():
            pattern = self._name_regex(name)
            match = re.match(pattern, text, re.IGNORECASE)
            if not match:
                continue
            return name, text[match.end() :].strip()
        return '', text

    def _consume_token(
        self,
        tokens: list[str],
        index: int,
        options: dict[str, str],
        flags: set[str],
        rest_parts: list[str],
    ) -> int:
        token = tokens[index]
        opt = self._try_match_option(token, options)
        if opt:
            options[opt[0]] = opt[1]
            return index + 1

        positional = self._try_positional_option(tokens, index, options)
        if positional:
            options[token] = positional
            return index + 2

        flag = self._try_match_flag(token, flags)
        if flag:
            flags.add(flag)
            return index + 1

        rest_parts.append(token)
        return index + 1

    def _try_positional_option(
        self,
        tokens: list[str],
        index: int,
        options: dict[str, str],
    ) -> str | None:
        if index + 1 >= len(tokens):
            return None
        value = self._try_match_option_as_value(tokens[index + 1])
        if value is None or value in options:
            return None
        return value

    def _try_match_option_as_value(self, token: str) -> str | None:
        for opt in self._config.options:
            for value in opt.values:
                if re.match(f'^{self._escape(value)}$', token, re.IGNORECASE):
                    return value
        return None

    def _try_match_option(self, token: str, matched: dict[str, str]) -> tuple[str, str] | None:
        for opt in self._config.options:
            if opt.name in matched:
                continue
            value = self._match_option_value(opt, token)
            if value is not None:
                return opt.name, value
        return None

    def _match_option_value(self, opt: 'OptionDef', token: str) -> str | None:
        for value in opt.values:
            if re.match(f'^{self._escape(value)}$', token, re.IGNORECASE):
                return value
        if opt.pattern and re.match(f'^{opt.pattern}$', token, re.IGNORECASE):
            return token
        return None

    def _try_match_flag(self, token: str, matched: set[str]) -> str | None:
        for flag in self._config.flags:
            if flag in matched:
                continue
            if re.match(f'^{self._escape(flag)}$', token, re.IGNORECASE):
                return flag
        return None

    def _build_regex(self) -> re.Pattern[str]:
        from bot.domain.commands.base import ArgType

        parts: list[str] = [r'^\s*,\s*', self._build_name_alt()]

        token_alt = self._build_token_alt()
        if token_alt:
            parts.append(f'(?:\\s+(?:{token_alt}))*')

        parts.append(self._build_args_part(self._config.args, ArgType))
        return re.compile(''.join(parts), re.IGNORECASE)

    def _build_name_alt(self) -> str:
        patterns = [self._name_regex(name) for name in self._sorted_names()]
        if len(patterns) == 1:
            return patterns[0]
        return f'(?:{"|".join(patterns)})'

    def _build_token_alt(self) -> str:
        alternatives: list[str] = []
        for opt in self._config.options:
            if opt.values:
                values = sorted(opt.values, key=len, reverse=True)
                alternatives.append(f'(?:{"|".join(self._escape(v) for v in values)})')
            elif opt.pattern:
                alternatives.append(f'(?:{opt.pattern})')
        alternatives.extend(self._escape(flag) for flag in self._config.flags)
        return '|'.join(alternatives)

    def _build_args_part(self, args, arg_type) -> str:
        if args == arg_type.NONE:
            return r'\s*$'
        pattern = self._config.args_pattern
        if pattern:
            stripped = self._strip_anchors(pattern)
            return f'\\s*{stripped}\\s*$'
        if args == arg_type.REQUIRED:
            return r'\s+.+'
        return r'(?:\s+.*)?$'

    def _sorted_names(self) -> list[str]:
        return sorted([self._config.name, *self._config.aliases], key=len, reverse=True)

    def _name_regex(self, name: str) -> str:
        return self.INTERNAL_WHITESPACE.sub(r'\\s*', self._escape(name))

    @classmethod
    def _escape(cls, text: str) -> str:
        escaped = cls.METACHARS.sub(r'\\\g<0>', text)
        return cls.NON_ASCII.sub('.', escaped)

    @staticmethod
    def _strip_anchors(pattern: str) -> str:
        return pattern.removeprefix('^').removesuffix('$')
