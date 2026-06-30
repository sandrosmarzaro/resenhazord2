from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Database:
    _POOL_SIZE = 5

    _engine: AsyncEngine | None = None
    _sessionmaker: async_sessionmaker[AsyncSession] | None = None
    _url: str = ''

    @classmethod
    def configure(cls, url: str) -> None:
        cls._url = url

    @classmethod
    def engine(cls) -> AsyncEngine:
        if cls._engine is None:
            cls._engine = create_async_engine(cls._url, pool_size=cls._POOL_SIZE, max_overflow=0)
        return cls._engine

    @classmethod
    def session(cls) -> AsyncSession:
        if cls._sessionmaker is None:
            cls._sessionmaker = async_sessionmaker(cls.engine(), expire_on_commit=False)
        return cls._sessionmaker()

    @classmethod
    async def close(cls) -> None:
        if cls._engine is not None:
            await cls._engine.dispose()
        cls._engine = None
        cls._sessionmaker = None

    @classmethod
    def reset(cls) -> None:
        cls._engine = None
        cls._sessionmaker = None
