# Infra scopes (DISABLED/DEV/ADMIN/INTERNAL) are code-locked and never reach the
# per-group layer; only PUBLIC and NSFW are togglable (ADR 0012).

from bot.domain.commands.base import Category, CommandScope

TOGGLABLE_SCOPES: frozenset[CommandScope] = frozenset({CommandScope.PUBLIC, CommandScope.NSFW})

SCOPE_DEFAULT_ENABLED: dict[CommandScope, bool] = {
    CommandScope.PUBLIC: True,
    CommandScope.NSFW: False,
}

# ,config subtype shortcuts: a token expands to a set of togglable commands.
# 'nsfw' selects by scope; the rest select by category.
NSFW_SUBTYPE = 'nsfw'
SUBTYPE_CATEGORIES: dict[str, Category] = {
    Category.DOWNLOAD.value: Category.DOWNLOAD,
    Category.GROUP.value: Category.GROUP,
    Category.RANDOM.value: Category.RANDOM,
    Category.INFORMATION.value: Category.INFORMATION,
}
