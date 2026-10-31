import structlog
from motor.motor_asyncio import AsyncIOMotorCollection

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'
GROUP_NAME_FIELD = 'groups.name'


class RenameMentionList:
    async def execute(self, chat_jid: str, old_name: str, new_name: str) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            # array_filters, since the positional $ is undefined next to a $ne on its array.
            result = await col.update_one(
                {
                    '_id': chat_jid,
                    '$and': [{GROUP_NAME_FIELD: old_name}, {GROUP_NAME_FIELD: {'$ne': new_name}}],
                },
                {'$set': {'groups.$[target].name': new_name}},
                array_filters=[{'target.name': old_name}],
            )
            if not result.modified_count:
                return await self._refusal(col, chat_jid, old_name, new_name)
        except Exception:
            logger.exception('group_mentions_rename_error', chat_jid=chat_jid)
            return {'ok': False, 'message': f'Não consegui renomear o grupo *{old_name}* 😔'}
        return {'ok': True, 'old_name': old_name, 'new_name': new_name}

    @staticmethod
    async def _refusal(
        col: AsyncIOMotorCollection, chat_jid: str, old_name: str, new_name: str
    ) -> dict:
        # The update already decided; this read only picks the message.
        if await col.find_one({'_id': chat_jid, GROUP_NAME_FIELD: old_name}):
            return {'ok': False, 'message': f'Já existe um grupo com o nome *{new_name}* 😔'}
        return {'ok': False, 'message': f'Não existe um grupo com o nome *{old_name}* 😔'}
