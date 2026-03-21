"""Async MongoDB connection singleton using Motor."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

DATABASE_NAME = 'resenhazord2'


class MongoDBConnection:
    _client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
    _uri: str = ''

    @classmethod
    def configure(cls, uri: str) -> None:
        cls._uri = uri

    @classmethod
    def client(cls) -> AsyncIOMotorClient:  # type: ignore[type-arg]
        if cls._client is None:
            cls._client = AsyncIOMotorClient(cls._uri)
        return cls._client

    @classmethod
    def database(cls) -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
        return cls.client()[DATABASE_NAME]

    @classmethod
    def collection(cls, name: str) -> AsyncIOMotorCollection:  # type: ignore[type-arg]
        return cls.database()[name]

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            cls._client.close()
            cls._client = None

    @classmethod
    def reset(cls) -> None:
        cls._client = None
