from pymongo.errors import DuplicateKeyError

from bot.infrastructure.mongodb import MongoDBConnection


class IdempotentCounter:
    """A Mongo counter that counts each key once, so an at-least-once redelivery
    (ADR 0001) doesn't bump it twice."""

    DOCUMENT_ID = 'counter'
    RECENT_FIELD = 'recent_keys'
    # Redelivery comes within minutes, so only the latest keys need remembering.
    RECENT_LIMIT = 50

    def __init__(self, collection: str, field: str) -> None:
        self._collection = collection
        self._field = field

    async def increment(self, key: str | None) -> int:
        if key is None:
            return await self._increment({'_id': self.DOCUMENT_ID})
        try:
            return await self._increment(
                {'_id': self.DOCUMENT_ID, self.RECENT_FIELD: {'$ne': key}},
                {'$push': {self.RECENT_FIELD: {'$each': [key], '$slice': -self.RECENT_LIMIT}}},
            )
        except DuplicateKeyError:
            # The key was already counted: the filter missed, so the upsert tried a
            # second document with the same _id. A zero step reads the current count.
            return await self._increment({'_id': self.DOCUMENT_ID}, step=0)

    async def _increment(self, query: dict, extra_update: dict | None = None, step: int = 1) -> int:
        document = await MongoDBConnection.collection(self._collection).find_one_and_update(
            query,
            {'$inc': {self._field: step}, **(extra_update or {})},
            return_document=True,
            upsert=True,
        )
        return document[self._field]
