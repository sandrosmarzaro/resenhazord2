import re
from typing import ClassVar

from bot.adapters.whatsapp.port import WhatsAppPort
from bot.domain.commands.base import Command


class CommandRegistry:
    _instance: 'CommandRegistry | None' = None
    _LEADING_TOKEN_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'^\s*,\s*([\w-]+)')

    def __init__(self) -> None:
        self._commands: list[Command] = []
        self._by_name: dict[str, Command] = {}

    @classmethod
    def instance(cls) -> 'CommandRegistry':
        if cls._instance is None:
            cls._instance = CommandRegistry()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register(self, command: Command) -> None:
        self._commands.append(command)
        config = command.config
        self._by_name[config.name.lower()] = command
        for alias in config.aliases:
            self._by_name[alias.lower()] = command

    def set_whatsapp(self, whatsapp: WhatsAppPort) -> None:
        """Inject the WhatsApp port into all commands after WebSocket connects."""
        for cmd in self._commands:
            cmd._whatsapp = whatsapp

    def get_strategy(self, text: str) -> Command | None:
        candidate = self._lookup_by_leading_token(text)
        if candidate is not None and candidate.matches(text):
            return candidate
        for cmd in self._commands:
            if cmd is candidate:
                continue
            if cmd.matches(text):
                return cmd
        for cmd in self._commands:
            parsed = cmd.parse(text)
            if parsed.command_name:
                return cmd
        return None

    def get_by_name(self, name: str) -> Command | None:
        return self._by_name.get(name.lower())

    def get_all(self) -> list[Command]:
        return list(self._commands)

    def _lookup_by_leading_token(self, text: str) -> Command | None:
        match = self._LEADING_TOKEN_PATTERN.match(text)
        if not match:
            return None
        return self._by_name.get(match.group(1).lower())
