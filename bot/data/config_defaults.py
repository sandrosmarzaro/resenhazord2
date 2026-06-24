# Infra scopes (DISABLED/DEV/ADMIN/INTERNAL) are code-locked and never reach the
# per-group layer; only PUBLIC and NSFW are togglable (ADR 0012).

from bot.domain.commands.base import CommandScope

TOGGLABLE_SCOPES: frozenset[CommandScope] = frozenset({CommandScope.PUBLIC, CommandScope.NSFW})

SCOPE_DEFAULT_ENABLED: dict[CommandScope, bool] = {
    CommandScope.PUBLIC: True,
    CommandScope.NSFW: False,
}
