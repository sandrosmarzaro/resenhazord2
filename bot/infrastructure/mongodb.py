"""Async MongoDB connection singleton using Motor."""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase


class MongoDBConnection:
    _client: AsyncIOMotorClient[Any] | None = None
    _uri: str = ''
    _db_name: str = 'resenhazord2'

    @classmethod
    def configure(cls, uri: str, db_name: str = 'resenhazord2') -> None:
        cls._uri = uri
        cls._db_name = db_name

    @classmethod
    def client(cls) -> AsyncIOMotorClient[Any]:
        if cls._client is None:
            cls._client = AsyncIOMotorClient(cls._uri)
        return cls._client

    @classmethod
    def database(cls) -> AsyncIOMotorDatabase[Any]:
        return cls.client()[cls._db_name]

    @classmethod
    def collection(cls, name: str) -> AsyncIOMotorCollection[Any]:
        return cls.database()[name]

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            cls._client.close()
            cls._client = None

    @classmethod
    def reset(cls) -> None:
        cls._client = None
