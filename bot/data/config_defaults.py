from bot.domain.commands.base import Category, CommandScope

TOGGLABLE_SCOPES: frozenset[CommandScope] = frozenset({CommandScope.PUBLIC, CommandScope.NSFW})

SCOPE_DEFAULT_ENABLED: frozendict[CommandScope, bool] = frozendict(
    {
        CommandScope.PUBLIC: True,
        CommandScope.NSFW: False,
    }
)

NSFW_SUBTYPE = 'nsfw'
SUBTYPE_CATEGORIES: frozendict[str, Category] = frozendict(
    {
        Category.DOWNLOAD.value: Category.DOWNLOAD,
        Category.GROUP.value: Category.GROUP,
        Category.RANDOM.value: Category.RANDOM,
        Category.INFORMATION.value: Category.INFORMATION,
    }
)
