"""Port of src/parsers/CommandParser.ts to Python.

Builds a regex from CommandConfig for matching, and tokenizes text for parsing.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.domain.commands.base import CommandConfig, ParsedCommand


class CommandParser:
    def __init__(self, config: 'CommandConfig') -> None:
        self._config = config
        self._regex = self._build_regex()

    def matches(self, text: str) -> bool:
        return self._regex.search(text) is not None

    def parse(self, text: str) -> 'ParsedCommand':
        from bot.domain.commands.base import ParsedCommand

        remaining = re.sub(r'^\s*,\s*', '', text)

        command_name = ''
        names = [self._config.name, *self._config.aliases]
        for name in names:
            name_pattern = re.sub(r'\s+', r'\\s*', self._replace_diacritics(name))
            match = re.match(name_pattern, remaining, re.IGNORECASE)
            if match:
                command_name = name
                remaining = remaining[match.end() :].strip()
                break

        flags: set[str] = set()
        options: dict[str, str] = {}
        rest_parts: list[str] = []

        tokens = [t for t in remaining.split() if t]

        for token in tokens:
            opt = self._try_match_option(token, options)
            if opt:
                options[opt[0]] = opt[1]
                continue

            flag = self._try_match_flag(token, flags)
            if flag:
                flags.add(flag)
                continue

            rest_parts.append(token)

        return ParsedCommand(
            command_name=command_name,
            flags=flags,
            options=options,
            rest=' '.join(rest_parts),
        )

    def _try_match_option(self, token: str, matched: dict[str, str]) -> tuple[str, str] | None:
        for opt in self._config.options:
            if opt.name in matched:
                continue
            if opt.values:
                for v in opt.values:
                    pattern = self._replace_diacritics(v)
                    if re.match(f'^{pattern}$', token, re.IGNORECASE):
                        return (opt.name, v)
            if opt.pattern and re.match(f'^{opt.pattern}$', token, re.IGNORECASE):
                return (opt.name, token)
        return None

    def _try_match_flag(self, token: str, matched: set[str]) -> str | None:
        for f in self._config.flags:
            if f in matched:
                continue
            pattern = self._replace_diacritics(f)
            if re.match(f'^{pattern}$', token, re.IGNORECASE):
                return f
        return None

    def _build_regex(self) -> re.Pattern[str]:
        from bot.domain.commands.base import ArgType

        parts: list[str] = []

        parts.append(r'^\s*,\s*')

        names = [self._config.name, *self._config.aliases]
        name_patterns = [re.sub(r'\s+', r'\\s*', self._replace_diacritics(n)) for n in names]
        if len(name_patterns) == 1:
            parts.append(name_patterns[0])
        else:
            parts.append(f'(?:{"|".join(name_patterns)})')

        for opt in self._config.options:
            if opt.values:
                sorted_values = sorted(opt.values, key=len, reverse=True)
                val_patterns = [self._replace_diacritics(v) for v in sorted_values]
                parts.append(f'\\s*(?:{"|".join(val_patterns)})?')
            elif opt.pattern:
                parts.append(f'\\s*(?:{opt.pattern})?')

        if self._config.flags:
            flag_patterns = [self._replace_diacritics(f) for f in self._config.flags]
            parts.append(f'(?:\\s+(?:{"|".join(flag_patterns)}))*')

        args = self._config.args
        if args == ArgType.NONE:
            parts.append(r'\s*$')
        elif args == ArgType.REQUIRED:
            if self._config.args_pattern:
                src = self._strip_anchors(self._config.args_pattern)
                parts.append(f'\\s*{src}\\s*$')
            else:
                parts.append(r'\s+.+')
        elif args == ArgType.OPTIONAL:
            if self._config.args_pattern:
                src = self._strip_anchors(self._config.args_pattern)
                parts.append(f'\\s*{src}\\s*$')
            else:
                parts.append(r'(?:\s+.*)?$')

        return re.compile(''.join(parts), re.IGNORECASE)

    @staticmethod
    def _replace_diacritics(s: str) -> str:
        # Escape ASCII regex metacharacters, then replace non-ASCII with '.'
        escaped = re.sub(r'[.*+?^${}()|[\]\\]', r'\\\g<0>', s)
        return re.sub(r'[^\x00-\x7f]', '.', escaped)

    @staticmethod
    def _strip_anchors(pattern: str) -> str:
        return pattern.removeprefix('^').removesuffix('$')
