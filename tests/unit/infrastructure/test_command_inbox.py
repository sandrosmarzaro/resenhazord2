import pytest
from fakeredis.aioredis import FakeRedis

from bot.infrastructure.command_inbox import RedisCommandInbox


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def redis():
    return FakeRedis()


class TestDone:
    @pytest.mark.anyio
    async def test_unknown_command_is_not_done(self, redis):
        inbox = RedisCommandInbox(redis)

        assert await inbox.is_done('g@g.us:MSG-1') is False

    @pytest.mark.anyio
    async def test_marked_command_is_done(self, redis):
        inbox = RedisCommandInbox(redis)

        await inbox.mark_done('g@g.us:MSG-1')

        assert await inbox.is_done('g@g.us:MSG-1') is True

    @pytest.mark.anyio
    async def test_mark_expires_after_the_retention(self, redis):
        inbox = RedisCommandInbox(redis)

        await inbox.mark_done('g@g.us:MSG-1')

        assert await redis.ttl('command_done:g@g.us:MSG-1') == RedisCommandInbox.RETENTION_SECONDS


class TestRedisDown:
    @pytest.mark.anyio
    async def test_is_done_fails_open(self):
        inbox = RedisCommandInbox.from_url('redis://127.0.0.1:1')

        assert await inbox.is_done('g@g.us:MSG-1') is False

    @pytest.mark.anyio
    async def test_mark_done_does_not_raise(self):
        inbox = RedisCommandInbox.from_url('redis://127.0.0.1:1')

        await inbox.mark_done('g@g.us:MSG-1')
