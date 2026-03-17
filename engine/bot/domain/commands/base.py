from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

from bot.adapters.whatsapp.port import WhatsAppPort
from bot.domain.builders.reply import Reply
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.parsers.command_parser import CommandParser


class ArgType(StrEnum):
    NONE = 'none'
    REQUIRED = 'required'
    OPTIONAL = 'optional'


@dataclass(frozen=True)
class OptionDef:
    name: str
    values: list[str] = field(default_factory=list)
    pattern: str | None = None


@dataclass(frozen=True)
class CommandConfig:
    name: str
    aliases: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    options: list[OptionDef] = field(default_factory=list)
    args: ArgType = ArgType.NONE
    args_pattern: str | None = None
    args_label: str | None = None
    group_only: bool = False
    category: str | None = None


@dataclass
class ParsedCommand:
    command_name: str
    flags: set[str] = field(default_factory=set)
    options: dict[str, str] = field(default_factory=dict)
    rest: str = ''


class Command(ABC):
    def __init__(self, whatsapp: WhatsAppPort | None = None) -> None:
        self._whatsapp = whatsapp
        self._parser: CommandParser | None = None

    @property
    def parser(self) -> CommandParser:
        if self._parser is None:
            self._parser = CommandParser(self.config)
        return self._parser

    @property
    @abstractmethod
    def config(self) -> CommandConfig: ...

    @property
    @abstractmethod
    def menu_description(self) -> str: ...

    def matches(self, text: str) -> bool:
        return self.parser.matches(text)

    async def run(self, data: CommandData) -> list[BotMessage]:
        if self.config.group_only and not data.is_group:
            return [Reply.to(data).text('Esse comando só funciona em grupo! 🤦‍♂️')]
        parsed = self.parser.parse(data.text)
        messages = await self.execute(data, parsed)
        return self._apply_flags(data, parsed, messages)

    @abstractmethod
    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]: ...

    def _apply_flags(
        self, data: CommandData, parsed: ParsedCommand, messages: list[BotMessage]
    ) -> list[BotMessage]:
        for msg in messages:
            if 'dm' in parsed.flags and data.participant:
                msg.jid = data.participant
            if 'show' in parsed.flags and hasattr(msg.content, 'view_once'):
                msg.content.view_once = False  # type: ignore[union-attr]
        return messages
