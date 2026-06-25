import pytest
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from bot.domain.models.chat_config import ChatKey, ChatPolicy, ChatType
from bot.infrastructure.config_store import SqlConfigStore
from bot.infrastructure.database import Database
from bot.infrastructure.models import Base


@pytest.fixture(scope='module')
def database_url():
    with PostgresContainer('postgres:17-alpine') as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        yield (
            f'postgresql+asyncpg://{container.username}:{container.password}'
            f'@{host}:{port}/{container.dbname}'
        )


@pytest.fixture
async def store(database_url):
    Database.reset()
    Database.configure(database_url)
    async with Database.engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(text('TRUNCATE chat, command_override RESTART IDENTITY CASCADE'))

    yield SqlConfigStore()

    await Database.close()


def group_key(native_id: str = '120@g.us') -> ChatKey:
    return ChatKey(platform='whatsapp', native_id=native_id, type=ChatType.GROUP)


class TestLoad:
    @pytest.mark.anyio
    async def test_unknown_chat_returns_open_default(self, store):
        config = await store.load('whatsapp', 'never-seen@g.us')

        assert config.policy is ChatPolicy.OPEN
        assert config.overrides == {}

    @pytest.mark.anyio
    async def test_reflects_a_stored_override(self, store):
        await store.set_override(group_key(), 'hentai', enabled=True)

        config = await store.load('whatsapp', '120@g.us')

        assert config.override_for('hentai') is True


class TestSetOverride:
    @pytest.mark.anyio
    async def test_creates_chat_and_override(self, store):
        await store.set_override(group_key(), 'fuck', enabled=False)

        config = await store.load('whatsapp', '120@g.us')

        assert config.overrides == {'fuck': False}

    @pytest.mark.anyio
    async def test_second_write_updates_not_duplicates(self, store):
        await store.set_override(group_key(), 'fuck', enabled=False)
        await store.set_override(group_key(), 'fuck', enabled=True)

        config = await store.load('whatsapp', '120@g.us')

        assert config.overrides == {'fuck': True}


class TestClearOverride:
    @pytest.mark.anyio
    async def test_removes_the_override(self, store):
        await store.set_override(group_key(), 'fuck', enabled=False)

        await store.clear_override(group_key(), 'fuck')

        config = await store.load('whatsapp', '120@g.us')
        assert config.overrides == {}

    @pytest.mark.anyio
    async def test_clear_on_unknown_chat_is_noop(self, store):
        await store.clear_override(group_key('absent@g.us'), 'fuck')

        config = await store.load('whatsapp', 'absent@g.us')
        assert config.overrides == {}


class TestSetPolicy:
    @pytest.mark.anyio
    async def test_sets_curated_policy(self, store):
        await store.set_policy(group_key(), ChatPolicy.CURATED)

        config = await store.load('whatsapp', '120@g.us')

        assert config.policy is ChatPolicy.CURATED
