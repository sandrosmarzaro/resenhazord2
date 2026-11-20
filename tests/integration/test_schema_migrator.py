from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from bot.infrastructure.schema_migrator import SchemaMigrator

ALEMBIC_INI = Path(__file__).resolve().parents[2] / 'alembic.ini'
CHAT_TABLES = '21e07392eca2'
DEV_ADMIN = '04501864102e'


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
async def engine(database_url):
    engine = create_async_engine(database_url)
    yield engine
    await engine.dispose()


async def _schema(engine) -> tuple[str, set[str]]:
    async with engine.connect() as connection:
        revision = await connection.scalar(text('SELECT version_num FROM alembic_version'))
        tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    return revision, tables


async def _migrate(engine, step, revision: str) -> None:
    def run(connection) -> None:
        config = Config(ALEMBIC_INI)
        config.attributes['connection'] = connection
        step(config, revision)

    async with engine.begin() as connection:
        await connection.run_sync(run)


async def _chat_columns(engine) -> set[str]:
    async with engine.connect() as connection:
        columns = await connection.run_sync(lambda sync: inspect(sync).get_columns('chat'))
    return {column['name'] for column in columns}


class TestUpgrade:
    @pytest.mark.anyio
    async def test_brings_a_fresh_database_to_the_head_revision(self, engine):
        head = ScriptDirectory.from_config(Config(ALEMBIC_INI)).get_current_head()

        await SchemaMigrator.upgrade(engine)

        revision, tables = await _schema(engine)
        assert revision == head
        assert {'chat', 'command_override'} <= tables

    @pytest.mark.anyio
    async def test_running_again_on_the_next_boot_changes_nothing(self, engine):
        await SchemaMigrator.upgrade(engine)
        before = await _schema(engine)

        await SchemaMigrator.upgrade(engine)

        assert await _schema(engine) == before


class TestDevAdminRevision:
    @pytest.mark.anyio
    async def test_leaves_existing_chats_with_the_flag_off(self, engine):
        await _migrate(engine, command.downgrade, 'base')
        await _migrate(engine, command.upgrade, CHAT_TABLES)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    'INSERT INTO chat (id, platform, native_id, type, default_policy,'
                    " created_at, updated_at) VALUES (gen_random_uuid(), 'whatsapp',"
                    " '120@g.us', 'group', 'open', now(), now())"
                )
            )

        await _migrate(engine, command.upgrade, DEV_ADMIN)

        async with engine.connect() as connection:
            assert await connection.scalar(text('SELECT dev_admin FROM chat')) is False

    @pytest.mark.anyio
    async def test_downgrade_drops_the_column(self, engine):
        await _migrate(engine, command.upgrade, DEV_ADMIN)

        await _migrate(engine, command.downgrade, CHAT_TABLES)

        assert 'dev_admin' not in await _chat_columns(engine)
