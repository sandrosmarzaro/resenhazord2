from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from bot.infrastructure.schema_migrator import SchemaMigrator

ALEMBIC_INI = Path(__file__).resolve().parents[2] / 'alembic.ini'


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
