from bot.data.currency import ASSET_GROUPS, ASSET_NAMES, GROUP_NAMES
from bot.domain.text import strip_accents


def test_every_name_points_to_a_quoted_asset():
    quoted = {code for group in ASSET_GROUPS for code in group.icons}

    assert set(ASSET_NAMES.values()) <= quoted


def test_names_are_lowercase_without_accents():
    names = [*ASSET_NAMES, *GROUP_NAMES]

    assert all(name == strip_accents(name.casefold()) for name in names)
