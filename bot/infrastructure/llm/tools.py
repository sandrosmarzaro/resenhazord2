"""Tool schema builder for LLM agent."""

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import ArgType, Command, CommandScope


def command_to_tool_schema(command: Command) -> dict:
    """Convert a Command to tool schema format for LLM tool calling.

    Format tested and confirmed working (NO 'required' field).
    """
    config = command.config
    properties: dict = {}

    for flag in config.flags:
        properties[flag] = {'type': 'boolean'}

    for option in config.options:
        if option.values:
            properties[option.name] = {
                'type': 'string',
                'enum': option.values,
            }
        elif option.pattern:
            properties[option.name] = {'type': 'string'}
        else:
            properties[option.name] = {'type': 'string'}

    if config.args != ArgType.NONE:
        properties['args'] = {'type': 'string'}

    def _to_ascii(name: str) -> str:
        replacements = {
            'ã': 'a',
            'á': 'a',
            'à': 'a',
            'â': 'a',
            'é': 'e',
            'ê': 'e',
            'í': 'i',
            'ó': 'o',
            'ô': 'o',
            'õ': 'o',
            'ú': 'u',
            'ç': 'c',
            ' ': '_',
        }
        return ''.join(replacements.get(ch, ch if ch.isascii() else '_') for ch in name.lower())

    ascii_name = _to_ascii(config.name)

    return {
        'type': 'function',
        'function': {
            'name': ascii_name,
            'description': command.menu_description or config.name,
            'parameters': {
                'type': 'object',
                'properties': properties,
            },
        },
    }


def build_tools_for_prompt(
    registry: CommandRegistry,
    include_scope: CommandScope = CommandScope.PUBLIC,
    exclude_scopes: frozenset[CommandScope] | None = None,
) -> list[dict]:
    """Build tool schemas filtered by scope.

    Args:
        registry: CommandRegistry instance
        include_scope: Only include commands with this scope or higher
        (PUBLIC < INTERNAL < DEV < ADMIN)
        exclude_scopes: Explicitly exclude these scopes
    """
    if exclude_scopes is None:
        exclude_scopes = frozenset()

    tools: list[dict] = []
    scope_priority = {
        CommandScope.PUBLIC: 0,
        CommandScope.INTERNAL: 1,
        CommandScope.DEV: 2,
        CommandScope.ADMIN: 3,
        CommandScope.NSFW: 4,
        CommandScope.DISABLED: 5,
    }

    for command in registry.get_all():
        cfg = command.config

        if cfg.scope in exclude_scopes:
            continue

        if cfg.scope == CommandScope.DISABLED:
            continue

        if include_scope != CommandScope.PUBLIC:
            min_priority = scope_priority.get(include_scope, 0)
            cmd_priority = scope_priority.get(cfg.scope, 0)
            if cmd_priority < min_priority:
                continue

        tools.append(command_to_tool_schema(command))

    return tools


def get_command_names(registry: CommandRegistry) -> list[str]:
    """Get list of all command names for prompt."""
    return [cmd.config.name for cmd in registry.get_all()]


def get_command_list_with_descriptions(registry: CommandRegistry) -> str:
    """Get formatted list of commands with descriptions."""
    lines = []
    for cmd in registry.get_all():
        name = cmd.config.name
        desc = cmd.menu_description or ''
        aliases = cmd.config.aliases or []
        names = f'{name} ({", ".join(aliases)})' if aliases else name
        lines.append(f'- {names}: {desc}' if desc else f'- {names}')
    return '\n'.join(lines)
