import re
import unicodedata
from typing import ClassVar

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import ArgType, Command, CommandScope


class _ToolBuilder:
    NON_ASCII_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'[^a-z0-9_-]')
    SCOPE_PRIORITY: ClassVar[dict[CommandScope, int]] = {
        CommandScope.PUBLIC: 0,
        CommandScope.INTERNAL: 1,
        CommandScope.DEV: 2,
        CommandScope.ADMIN: 3,
        CommandScope.NSFW: 4,
        CommandScope.DISABLED: 5,
    }

    @classmethod
    def to_ascii_name(cls, name: str) -> str:
        normalized = unicodedata.normalize('NFD', name.lower())
        stripped = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
        return cls.NON_ASCII_PATTERN.sub('_', stripped.replace(' ', '_'))


def command_to_tool_schema(command: Command) -> dict:
    config = command.config
    properties: dict = {}

    for flag in config.flags:
        properties[flag] = {'type': 'boolean'}

    for option in config.options:
        if option.values:
            properties[option.name] = {'type': 'string', 'enum': option.values}
        else:
            properties[option.name] = {'type': 'string'}

    if config.args != ArgType.NONE:
        properties['args'] = {'type': 'string'}

    return {
        'type': 'function',
        'function': {
            'name': _ToolBuilder.to_ascii_name(config.name),
            'description': command.menu_description or config.name,
            'parameters': {'type': 'object', 'properties': properties},
        },
    }


def build_tools_for_prompt(
    registry: CommandRegistry,
    include_scope: CommandScope = CommandScope.PUBLIC,
    exclude_scopes: frozenset[CommandScope] | None = None,
) -> list[dict]:
    excluded = exclude_scopes if exclude_scopes is not None else frozenset({CommandScope.NSFW})
    min_priority = _ToolBuilder.SCOPE_PRIORITY.get(include_scope, 0)

    tools: list[dict] = []
    for command in registry.get_all():
        scope = command.config.scope
        if scope in excluded or scope == CommandScope.DISABLED:
            continue
        if (
            include_scope != CommandScope.PUBLIC
            and _ToolBuilder.SCOPE_PRIORITY.get(scope, 0) < min_priority
        ):
            continue
        tools.append(command_to_tool_schema(command))
    return tools


def get_command_names(registry: CommandRegistry) -> list[str]:
    return [cmd.config.name for cmd in registry.get_all()]


def get_command_list_with_descriptions(registry: CommandRegistry) -> str:
    lines = []
    for cmd in registry.get_all():
        name = cmd.config.name
        desc = cmd.menu_description or ''
        aliases = cmd.config.aliases or []
        names = f'{name} ({", ".join(aliases)})' if aliases else name
        lines.append(f'- {names}: {desc}' if desc else f'- {names}')
    return '\n'.join(lines)
