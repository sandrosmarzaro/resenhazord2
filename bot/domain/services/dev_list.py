"""Dev list service — manages developer JIDs in MongoDB."""

from bot.infrastructure.mongodb import MongoDBConnection


class DevListService:
    COLLECTION = 'dev_list'

    async def is_dev(self, jid: str) -> bool:
        col = MongoDBConnection.collection(self.COLLECTION)
        return await col.find_one({'_id': jid}) is not None

    async def add(self, jid: str) -> bool:
        col = MongoDBConnection.collection(self.COLLECTION)
        result = await col.update_one({'_id': jid}, {'$set': {'_id': jid}}, upsert=True)
        return result.upserted_id is not None

    async def remove(self, jid: str) -> bool:
        col = MongoDBConnection.collection(self.COLLECTION)
        result = await col.delete_one({'_id': jid})
        return result.deleted_count > 0

    async def list_all(self) -> list[str]:
        col = MongoDBConnection.collection(self.COLLECTION)
        return [doc['_id'] async for doc in col.find()]
