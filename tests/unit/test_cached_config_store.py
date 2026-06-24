import pytest

from bot.domain.models.chat_config import ChatConfig, ChatKey, ChatPolicy, ChatType
from bot.infrastructure.cached_config_store import CachedConfigStore


def group_key() -> ChatKey:
    return ChatKey(platform='whatsapp', native_id='120@g.us', type=ChatType.GROUP)


class TestLoad:
    @pytest.mark.anyio
    async def test_caches_within_ttl(self, mocker):
        store = mocker.AsyncMock()
        config = ChatConfig(policy=ChatPolicy.OPEN)
        store.load.return_value = config
        cached = CachedConfigStore(store)

        first = await cached.load('whatsapp', '120@g.us')
        second = await cached.load('whatsapp', '120@g.us')

        assert first is second
        store.load.assert_awaited_once_with('whatsapp', '120@g.us')

    @pytest.mark.anyio
    async def test_expires_after_ttl(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        mocker.patch(
            'bot.infrastructure.cached_config_store.monotonic',
            side_effect=[0.0, 100.0],
        )
        cached = CachedConfigStore(store)

        await cached.load('whatsapp', '120@g.us')
        await cached.load('whatsapp', '120@g.us')

        assert store.load.await_count == 2


class TestWriteInvalidation:
    @pytest.mark.anyio
    async def test_set_override_invalidates_and_delegates(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        cached = CachedConfigStore(store)

        await cached.load('whatsapp', '120@g.us')
        await cached.set_override(group_key(), 'oi', enabled=False)
        await cached.load('whatsapp', '120@g.us')

        assert store.load.await_count == 2
        store.set_override.assert_awaited_once_with(group_key(), 'oi', enabled=False)

    @pytest.mark.anyio
    async def test_set_policy_invalidates(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        cached = CachedConfigStore(store)

        await cached.load('whatsapp', '120@g.us')
        await cached.set_policy(group_key(), ChatPolicy.CURATED)
        await cached.load('whatsapp', '120@g.us')

        assert store.load.await_count == 2
        store.set_policy.assert_awaited_once_with(group_key(), ChatPolicy.CURATED)
