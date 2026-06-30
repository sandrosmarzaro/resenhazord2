from bot.domain.commands.base import Category, CommandScope

TOGGLABLE_SCOPES: frozenset[CommandScope] = frozenset({CommandScope.PUBLIC, CommandScope.NSFW})

SCOPE_DEFAULT_ENABLED: dict[CommandScope, bool] = {
    CommandScope.PUBLIC: True,
    CommandScope.NSFW: False,
}

NSFW_SUBTYPE = 'nsfw'
SUBTYPE_CATEGORIES: dict[str, Category] = {
    Category.DOWNLOAD.value: Category.DOWNLOAD,
    Category.GROUP.value: Category.GROUP,
    Category.RANDOM.value: Category.RANDOM,
    Category.INFORMATION.value: Category.INFORMATION,
}
