import structlog
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from bot.domain.jid import normalize_jid, normalize_jids
from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class CreateMentionList:
    async def execute(
        self,
        chat_jid: str,
        sender_jid: str,
        group_name: str,
        mentioned: list[str],
    ) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            participants = list(
                dict.fromkeys([normalize_jid(sender_jid), *normalize_jids(mentioned)])
            )
            group = {'name': group_name, 'participants': participants}
            if not await self._push_unless_taken(col, chat_jid, group):
                return {
                    'ok': False,
                    'message': f'Já existe um grupo com o nome *{group_name}* 😔',
                }
        except Exception:
            logger.exception('group_mentions_create_error', chat_jid=chat_jid)
            return {'ok': False, 'message': f'Não consegui criar o grupo *{group_name}* 😔'}
        return {'ok': True, 'group_name': group_name}

    @staticmethod
    async def _push_unless_taken(col: AsyncIOMotorCollection, chat_jid: str, group: dict) -> bool:
        # A single-document update is atomic, and the name check lives in its filter: a
        # unique index couldn't help, since it doesn't apply within one document's array.
        query = {'_id': chat_jid, 'groups.name': {'$ne': group['name']}}
        update = {'$push': {'groups': group}}
        try:
            await col.update_one(query, update, upsert=True)
        except DuplicateKeyError:
            # The filter missed: the name is taken, or another create just made the document.
            result = await col.update_one(query, update)
            return result.modified_count == 1
        return True
