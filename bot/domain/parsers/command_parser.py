"""Tokenises command text against a CommandConfig regex into a ParsedCommand."""

import re
from typing import TYPE_CHECKING, ClassVar

from bot.domain.parsers.command_parser_regex import CommandParserRegex

if TYPE_CHECKING:
    from bot.domain.commands.base import CommandConfig, OptionDef, ParsedCommand


class CommandParser:
    LEADING_COMMA: ClassVar[re.Pattern[str]] = re.compile(r'^\s*,\s*')

    def __init__(self, config: 'CommandConfig') -> None:
        self._config = config
        self._regex = CommandParserRegex.build(config)

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
        for name in CommandParserRegex.sorted_names(self._config):
            pattern = CommandParserRegex.name_pattern(name)
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
                if re.match(f'^{CommandParserRegex.escape(value)}$', token, re.IGNORECASE):
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

    @staticmethod
    def _match_option_value(opt: 'OptionDef', token: str) -> str | None:
        for value in opt.values:
            if re.match(f'^{CommandParserRegex.escape(value)}$', token, re.IGNORECASE):
                return value
        if opt.pattern and re.match(f'^{opt.pattern}$', token, re.IGNORECASE):
            return token
        return None

    def _try_match_flag(self, token: str, matched: set[str]) -> str | None:
        for flag in self._config.flags:
            if flag in matched:
                continue
            if re.match(f'^{CommandParserRegex.escape(flag)}$', token, re.IGNORECASE):
                return flag
        return None
