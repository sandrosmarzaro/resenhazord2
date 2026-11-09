from pathlib import Path
from typing import ClassVar

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


class SchemaMigrator:
    # Migrating inside the app process spares the core node a second interpreter that
    # re-imports the bot, the slowest part of a boot under CPU steal.
    ALEMBIC_INI: ClassVar[Path] = Path(__file__).resolve().parents[2] / 'alembic.ini'

    @classmethod
    async def upgrade(cls, engine: AsyncEngine) -> None:
        async with engine.begin() as connection:
            await connection.run_sync(cls._upgrade_to_head)

    @classmethod
    def _upgrade_to_head(cls, connection: Connection) -> None:
        config = Config(cls.ALEMBIC_INI)
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
