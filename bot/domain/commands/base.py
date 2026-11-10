import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

import structlog
from opentelemetry import trace
from opentelemetry.trace import StatusCode, Tracer

from bot.adapters.whatsapp.port import WhatsAppPort
from bot.domain.builders.reply import Reply
from bot.domain.exceptions import BotError, ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.contents.audio_content import AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage
from bot.domain.parsers.command_parser import CommandParser
from bot.domain.services.voice_note import VoiceNote

logger = structlog.get_logger()


class ArgType(StrEnum):
    NONE = 'none'
    REQUIRED = 'required'
    OPTIONAL = 'optional'


class Flag(StrEnum):
    DM = 'dm'
    SHOW = 'show'
    STATUS = 'status'


class Platform(StrEnum):
    WHATSAPP = 'whatsapp'
    DISCORD = 'discord'
    TELEGRAM = 'telegram'
    ALL = 'all'

    @classmethod
    def supports(cls, declared: list['Platform'], target: 'Platform | str') -> bool:
        return cls.ALL in declared or target in declared


class Category(StrEnum):
    RANDOM = 'random'
    DOWNLOAD = 'download'
    GROUP = 'group'
    INFORMATION = 'info'
    OTHER = 'other'


class CommandScope(StrEnum):
    PUBLIC = 'public'
    INTERNAL = 'internal'
    DISABLED = 'disabled'
    ADMIN = 'admin'
    NSFW = 'nsfw'
    DEV = 'dev'


@dataclass(frozen=True)
class OptionDef:
    name: str
    values: list[str] = field(default_factory=list)
    pattern: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class CommandConfig:
    name: str
    aliases: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    options: list[OptionDef] = field(default_factory=list)
    args: ArgType = ArgType.NONE
    args_pattern: str | None = None
    args_label: str | None = None
    scope: CommandScope = CommandScope.PUBLIC
    group_only: bool = False
    category: Category | None = None
    platforms: list[Platform] = field(default_factory=lambda: [Platform.WHATSAPP])
    # Runs alone, from match until its reply is published, to bound peak memory.
    exclusive: bool = False

    # Every command whose media can go out without view-once can also go out as a
    # group status, so the one flag implies the other.
    def __post_init__(self) -> None:
        if Flag.SHOW in self.flags and Flag.STATUS not in self.flags:
            object.__setattr__(self, 'flags', [*self.flags, Flag.STATUS])


@dataclass
class ParsedCommand:
    command_name: str
    flags: set[str] = field(default_factory=set)
    options: dict[str, str] = field(default_factory=dict)
    rest: str = ''

    def number(self, option: str) -> int:
        digits = ''.join(filter(str.isdigit, self.options.get(option, '')))
        return int(digits or 0)


class Command(ABC):
    # The one span every platform's run goes through: spanmetrics turns its
    # dimensions into per-command, per-platform latency and error rate.
    _TRACER: ClassVar[Tracer] = trace.get_tracer(__name__)
    _OUTCOME: ClassVar[str] = 'command.outcome'
    _MS_PER_SECOND: ClassVar[int] = 1000
    STATUS_ONLY_IN_GROUPS: ClassVar[str] = 'O *status* só funciona em grupo do WhatsApp! 📸'
    _VIEW_ONCE_TYPES: ClassVar[tuple[type, ...]] = (
        ImageContent,
        ImageBufferContent,
        VideoContent,
        VideoBufferContent,
        AudioContent,
    )

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

    def parse(self, text: str) -> ParsedCommand:
        return self.parser.parse(text)

    async def run(self, data: CommandData) -> list[BotMessage]:
        attributes = {
            'command.name': self.config.name,
            'platform': data.platform or Platform.WHATSAPP,
            'chat_type': 'group' if data.is_group else 'private',
        }
        started = time.monotonic()
        outcome, error_type = 'success', None
        # Exceptions are classified by hand: the automatic record would put the
        # message, URL and query secrets included, on a span Tempo keeps unscrubbed.
        with self._TRACER.start_as_current_span(
            'command.run',
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                return await self._run(data)
            except ExternalServiceError as error:
                outcome, error_type = 'external_error', type(error).__name__
                raise
            except BotError:
                outcome = 'bot_error'
                raise
            except Exception as error:
                outcome, error_type = 'unexpected_error', type(error).__name__
                raise
            finally:
                span.set_attribute(self._OUTCOME, outcome)
                if error_type:
                    span.set_status(StatusCode.ERROR, error_type)
                # The one event per command, same fields on every platform, for an
                # agent or a dashboard to query without knowing the call sites.
                logger.info(
                    'command_completed',
                    command=self.config.name,
                    platform=attributes['platform'],
                    chat_type=attributes['chat_type'],
                    chat=data.jid,
                    outcome=outcome,
                    error_type=error_type,
                    duration_ms=round((time.monotonic() - started) * self._MS_PER_SECOND),
                )

    async def _run(self, data: CommandData) -> list[BotMessage]:
        if self.config.group_only and not data.is_group:
            return [Reply.to(data).text('Ah, esse comando só funciona em grupo! 😊')]
        parsed = self.parser.parse(data.text)
        if Flag.STATUS in parsed.flags and not self._in_whatsapp_group(data):
            return [Reply.to(data).text(self.STATUS_ONLY_IN_GROUPS)]
        messages = self._apply_flags(data, parsed, await self.execute(data, parsed))
        return [await VoiceNote.for_status(message) for message in messages]

    @staticmethod
    def _in_whatsapp_group(data: CommandData) -> bool:
        return data.is_group and (data.platform or Platform.WHATSAPP) == Platform.WHATSAPP

    @abstractmethod
    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]: ...

    @property
    def whatsapp(self) -> WhatsAppPort:
        if self._whatsapp is None:
            msg = f'{type(self).__name__} requires WhatsAppPort but none was injected'
            raise RuntimeError(msg)
        return self._whatsapp

    async def _get_media(self, data: CommandData) -> bytes:
        """Return proactively-downloaded media buffer, or fall back to wa_call."""
        if data.media_buffer is not None:
            return data.media_buffer
        if data.message_id is None or data.media_source is None:
            msg = 'No media buffer and no message_id/media_source to download from'
            raise RuntimeError(msg)
        return await self.whatsapp.download_media(data.message_id, data.media_source)

    def _apply_flags(
        self, data: CommandData, parsed: ParsedCommand, messages: list[BotMessage]
    ) -> list[BotMessage]:
        status = Flag.STATUS in parsed.flags
        for msg in messages:
            if Flag.DM in parsed.flags and data.participant:
                msg.jid = data.participant
            if (Flag.SHOW in parsed.flags or status) and isinstance(
                msg.content, self._VIEW_ONCE_TYPES
            ):
                msg.content.view_once = False
            msg.group_status = msg.group_status or status
        return messages
