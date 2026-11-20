import pytest

from bot.domain.models.blocked_member import BlockedMember
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
    async def test_keeps_a_quiet_chat_cached_between_commands(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        mocker.patch(
            'bot.infrastructure.cached_config_store.monotonic',
            side_effect=[0.0, 600.0],
        )
        cached = CachedConfigStore(store)

        await cached.load('whatsapp', '120@g.us')
        await cached.load('whatsapp', '120@g.us')

        store.load.assert_awaited_once_with('whatsapp', '120@g.us')

    @pytest.mark.anyio
    async def test_expires_after_ttl(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        mocker.patch(
            'bot.infrastructure.cached_config_store.monotonic',
            side_effect=[0.0, 3700.0],
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
    async def test_clear_override_invalidates_and_delegates(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        cached = CachedConfigStore(store)

        await cached.load('whatsapp', '120@g.us')
        await cached.clear_override(group_key(), 'oi')
        await cached.load('whatsapp', '120@g.us')

        assert store.load.await_count == 2
        store.clear_override.assert_awaited_once_with(group_key(), 'oi')

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

    @pytest.mark.anyio
    async def test_set_dev_admin_invalidates_and_delegates(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        cached = CachedConfigStore(store)

        await cached.load('whatsapp', '120@g.us')
        await cached.set_dev_admin(group_key(), enabled=True)
        await cached.load('whatsapp', '120@g.us')

        assert store.load.await_count == 2
        store.set_dev_admin.assert_awaited_once_with(group_key(), enabled=True)

    @pytest.mark.anyio
    async def test_block_members_invalidates_and_delegates(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        cached = CachedConfigStore(store)
        members = [BlockedMember(key='5527900000003@s.whatsapp.net')]

        await cached.load('whatsapp', '120@g.us')
        await cached.block_members(group_key(), members)
        await cached.load('whatsapp', '120@g.us')

        assert store.load.await_count == 2
        store.block_members.assert_awaited_once_with(group_key(), members)

    @pytest.mark.anyio
    async def test_unblock_members_invalidates_and_delegates(self, mocker):
        store = mocker.AsyncMock()
        store.load.return_value = ChatConfig()
        cached = CachedConfigStore(store)
        members = [BlockedMember(key='5527900000003@s.whatsapp.net')]

        await cached.load('whatsapp', '120@g.us')
        await cached.unblock_members(group_key(), members)
        await cached.load('whatsapp', '120@g.us')

        assert store.load.await_count == 2
        store.unblock_members.assert_awaited_once_with(group_key(), members)
