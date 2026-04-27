"""Translate LLM responses (tool calls or plain text) into CommandData."""

import json
import re
from dataclasses import replace
from typing import ClassVar

import structlog

from bot.application.command_registry import CommandRegistry
from bot.domain.models.command_data import CommandData

logger = structlog.get_logger()


class AgentResponseTranslator:
    DM_KEYWORDS: ClassVar[re.Pattern[str]] = re.compile(
        r'\b(privado|pv|dm|direct|mp|message\s*privately|send\s*(me\s*)?dm|send\s*(me\s*)?privately)\b',
        re.IGNORECASE,
    )
    LONG_FLAG_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'(\s)--(\w+)')
    LEADING_DASH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'^,+-')

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry

    @classmethod
    def normalize_flags(cls, text: str) -> str:
        text = cls.LONG_FLAG_PATTERN.sub(r'\1\2', text)
        return cls.LEADING_DASH_PATTERN.sub(',', text)

    def translate(
        self,
        data: CommandData,
        command_name: str,
        arguments: str,
    ) -> CommandData:
        command_text = self._compose_command_text(command_name, arguments)
        command_text = self._resolve_command_name(command_text)
        command_text, target_jid = self._apply_dm_redirect(command_text, data)
        command_text = self.normalize_flags(command_text)

        logger.info(
            'agent_mapped_command',
            original=data.text,
            mapped=command_text,
            dm_mode=target_jid != data.jid,
        )

        return replace(data, text=command_text, jid=target_jid)

    def _compose_command_text(self, command_name: str, arguments: str) -> str:
        try:
            args_dict = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            args_dict = {}

        command_name = command_name.lstrip('-')
        flags = [k.lstrip('-') for k, v in args_dict.items() if v is True]
        options = {
            k.lstrip('-'): v
            for k, v in args_dict.items()
            if v is not True and v is not False and k not in ('args', 'command')
        }
        text_args = args_dict.get('args', '')

        parts = [f',{command_name}']
        for name, value in options.items():
            parts.append(f'{name} {value}' if isinstance(value, str) else str(value))
        parts.extend(flag.lstrip('-') for flag in flags)
        if text_args:
            parts.append(text_args)

        return ' '.join(parts).strip('\'"')

    def _apply_dm_redirect(
        self,
        command_text: str,
        data: CommandData,
    ) -> tuple[str, str]:
        if not (data.is_group and self.DM_KEYWORDS.search(data.text)):
            return command_text, data.jid

        rewritten = self.DM_KEYWORDS.sub('', command_text).strip()
        if rewritten.startswith(','):
            rewritten = rewritten[1:].strip()
        return f',{rewritten}', data.sender_jid

    def _resolve_command_name(self, command_text: str) -> str:
        if not command_text.startswith(','):
            return command_text

        parts = command_text.split()
        if not parts:
            return command_text

        cmd = self._registry.get_by_name(parts[0][1:])
        if cmd:
            parts[0] = f',{cmd.config.name}'
        return ' '.join(parts)
