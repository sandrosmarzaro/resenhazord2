from dataclasses import replace

from bot.data.currency import ASSET_GROUPS, ASSET_NAMES, GROUP_NAMES, AssetGroup
from bot.domain.text import strip_accents


class AssetFilter:
    @staticmethod
    def groups(name: str) -> tuple[AssetGroup, ...] | None:
        key = strip_accents(name.casefold())
        if not key:
            return ASSET_GROUPS
        if key in GROUP_NAMES:
            return (GROUP_NAMES[key],)
        code = ASSET_NAMES.get(key, key).casefold()
        asset = next(
            (
                replace(group, icons=frozendict({asset: icon}))
                for group in ASSET_GROUPS
                for asset, icon in group.icons.items()
                if asset.casefold() == code
            ),
            None,
        )
        return (asset,) if asset else None
