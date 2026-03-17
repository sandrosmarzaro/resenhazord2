"""Port of src/parsers/CommandParser.ts to Python.

Builds a regex from CommandConfig for matching, and tokenizes text for parsing.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.domain.commands.base import CommandConfig, ParsedCommand


class CommandParser:
    def __init__(self, config: CommandConfig) -> None:
        self._config = config
        self._regex = self._build_regex()

    def matches(self, text: str) -> bool:
        return self._regex.search(text) is not None

    def parse(self, text: str) -> ParsedCommand:
        from bot.domain.commands.base import ParsedCommand

        remaining = re.sub(r"^\s*,\s*", "", text)

        command_name = ""
        names = [self._config.name, *self._config.aliases]
        for name in names:
            name_pattern = re.sub(r"\s+", r"\\s*", self._replace_diacritics(name))
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
            consumed = False

            for opt in self._config.options:
                if opt.name in options:
                    continue
                if opt.values:
                    matched_value = None
                    for v in opt.values:
                        pattern = self._replace_diacritics(v)
                        if re.match(f"^{pattern}$", token, re.IGNORECASE):
                            matched_value = v
                            break
                    if matched_value is not None:
                        options[opt.name] = matched_value
                        consumed = True
                        break
                if opt.pattern and re.match(f"^{opt.pattern}$", token, re.IGNORECASE):
                    options[opt.name] = token
                    consumed = True
                    break

            if not consumed:
                matched_flag = None
                for f in self._config.flags:
                    if f in flags:
                        continue
                    pattern = self._replace_diacritics(f)
                    if re.match(f"^{pattern}$", token, re.IGNORECASE):
                        matched_flag = f
                        break
                if matched_flag is not None:
                    flags.add(matched_flag)
                    consumed = True

            if not consumed:
                rest_parts.append(token)

        return ParsedCommand(
            command_name=command_name,
            flags=flags,
            options=options,
            rest=" ".join(rest_parts),
        )

    def _build_regex(self) -> re.Pattern[str]:
        from bot.domain.commands.base import ArgType

        parts: list[str] = []

        parts.append(r"^\s*,\s*")

        names = [self._config.name, *self._config.aliases]
        name_patterns = [re.sub(r"\s+", r"\\s*", self._replace_diacritics(n)) for n in names]
        if len(name_patterns) == 1:
            parts.append(name_patterns[0])
        else:
            parts.append(f"(?:{'|'.join(name_patterns)})")

        for opt in self._config.options:
            if opt.values:
                sorted_values = sorted(opt.values, key=len, reverse=True)
                val_patterns = [self._replace_diacritics(v) for v in sorted_values]
                parts.append(f"\\s*(?:{'|'.join(val_patterns)})?")
            elif opt.pattern:
                parts.append(f"\\s*(?:{opt.pattern})?")

        if self._config.flags:
            flag_patterns = [self._replace_diacritics(f) for f in self._config.flags]
            parts.append(f"(?:\\s+(?:{'|'.join(flag_patterns)}))*")

        args = self._config.args
        if args == ArgType.NONE:
            parts.append(r"\s*$")
        elif args == ArgType.REQUIRED:
            if self._config.args_pattern:
                src = self._strip_anchors(self._config.args_pattern)
                parts.append(f"\\s*{src}\\s*$")
            else:
                parts.append(r"\s+.+")
        elif args == ArgType.OPTIONAL:
            if self._config.args_pattern:
                src = self._strip_anchors(self._config.args_pattern)
                parts.append(f"\\s*{src}\\s*$")
            else:
                parts.append(r"(?:\s+.*)?$")

        return re.compile("".join(parts), re.IGNORECASE)

    @staticmethod
    def _replace_diacritics(s: str) -> str:
        # Escape ASCII regex metacharacters, then replace non-ASCII with '.'
        escaped = re.sub(r"[.*+?^${}()|[\]\\]", r"\\\g<0>", s)
        return re.sub(r"[^\x00-\x7f]", ".", escaped)

    @staticmethod
    def _strip_anchors(pattern: str) -> str:
        if pattern.startswith("^"):
            pattern = pattern[1:]
        if pattern.endswith("$"):
            pattern = pattern[:-1]
        return pattern
