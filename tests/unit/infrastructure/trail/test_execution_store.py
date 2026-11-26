import pytest
from fakeredis.aioredis import FakeRedis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from bot.infrastructure.execution_store import ExecutionStore

RECORD = {'execution': {'command': 'moeda', 'outcome': 'success'}}


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def redis():
    return FakeRedis()


class TestFind:
    @pytest.mark.anyio
    async def test_finds_the_record_by_any_reply_it_produced(self, redis):
        store = ExecutionStore(redis)
        await store.save(RECORD, 'whatsapp', 'g@g.us', ['3EB0A', '3EB0B'])

        found = await store.find('whatsapp', 'g@g.us', '3EB0B')

        assert found == RECORD

    @pytest.mark.anyio
    async def test_an_unknown_reply_has_no_record(self, redis):
        store = ExecutionStore(redis)

        assert await store.find('whatsapp', 'g@g.us', '3EB0A') is None

    @pytest.mark.anyio
    async def test_the_same_message_id_in_another_chat_is_another_reply(self, redis):
        store = ExecutionStore(redis)
        await store.save(RECORD, 'whatsapp', 'g@g.us', ['3EB0A'])

        assert await store.find('whatsapp', 'other@g.us', '3EB0A') is None

    @pytest.mark.anyio
    async def test_a_reply_whose_record_expired_has_none(self, redis):
        store = ExecutionStore(redis)
        await store.save(RECORD, 'discord', '42', ['7'])
        [record_key] = await redis.keys('execution:*')
        await redis.delete(record_key)

        assert await store.find('discord', '42', '7') is None


class TestSave:
    @pytest.mark.anyio
    async def test_every_key_expires_after_the_retention(self, redis):
        store = ExecutionStore(redis)

        await store.save(RECORD, 'telegram', '-100', ['1'])

        ttls = {await redis.ttl(key) for key in await redis.keys('*')}
        assert ttls == {ExecutionStore.RETENTION_SECONDS}

    @pytest.mark.anyio
    async def test_a_command_without_a_reply_stores_nothing(self, redis):
        store = ExecutionStore(redis)

        await store.save(RECORD, 'telegram', '-100', [])

        assert await redis.keys('*') == []

    @pytest.mark.anyio
    async def test_a_failed_write_does_not_raise(self):
        store = ExecutionStore(Redis.from_url('redis://127.0.0.1:1'))

        await store.save(RECORD, 'telegram', '-100', ['1'])


class TestWithoutRedis:
    @pytest.mark.anyio
    async def test_saving_is_a_no_op(self):
        await ExecutionStore(None).save(RECORD, 'telegram', '-100', ['1'])

    @pytest.mark.anyio
    async def test_nothing_is_found(self):
        assert await ExecutionStore(None).find('telegram', '-100', '1') is None


class TestInstance:
    @pytest.mark.anyio
    async def test_without_a_redis_url_the_store_is_off(self, monkeypatch):
        monkeypatch.setenv('REDIS_URL', '')
        ExecutionStore.reset()

        assert await ExecutionStore.instance().find('telegram', '-100', '1') is None

    def test_is_built_once(self, monkeypatch):
        monkeypatch.setenv('REDIS_URL', '')
        ExecutionStore.reset()

        assert ExecutionStore.instance() is ExecutionStore.instance()

    @pytest.mark.anyio
    async def test_with_a_redis_url_the_store_writes_there(self, monkeypatch):
        monkeypatch.setenv('REDIS_URL', 'redis://127.0.0.1:1')
        ExecutionStore.reset()

        with pytest.raises(RedisConnectionError):
            await ExecutionStore.instance().find('telegram', '-100', '1')
