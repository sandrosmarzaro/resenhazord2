# The bot is a single consumer on the core node, so a process-local cache stays
# coherent. If a second worker is ever added, swap invalidation for Upstash pub/sub.

from time import monotonic

from bot.domain.models.chat_config import ChatConfig, ChatKey, ChatPolicy
from bot.ports.config_store_port import ConfigStorePort


class CachedConfigStore:
    _TTL_SECONDS = 60.0

    def __init__(self, store: ConfigStorePort) -> None:
        self._store = store
        self._cache: dict[tuple[str, str], tuple[float, ChatConfig]] = {}

    async def load(self, platform: str, native_id: str) -> ChatConfig:
        cache_key = (platform, native_id)
        now = monotonic()
        cached = self._cache.get(cache_key)
        if cached is not None and now - cached[0] < self._TTL_SECONDS:
            return cached[1]
        config = await self._store.load(platform, native_id)
        self._cache[cache_key] = (now, config)
        return config

    async def set_override(self, key: ChatKey, command_name: str, *, enabled: bool) -> None:
        await self._store.set_override(key, command_name, enabled=enabled)
        self._invalidate(key)

    async def clear_override(self, key: ChatKey, command_name: str) -> None:
        await self._store.clear_override(key, command_name)
        self._invalidate(key)

    async def set_policy(self, key: ChatKey, policy: ChatPolicy) -> None:
        await self._store.set_policy(key, policy)
        self._invalidate(key)

    def _invalidate(self, key: ChatKey) -> None:
        self._cache.pop((key.platform, key.native_id), None)
