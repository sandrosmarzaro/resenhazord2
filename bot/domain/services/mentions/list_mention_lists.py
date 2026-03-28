import structlog

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class ListMentionLists:
    async def execute(self, chat_jid: str) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            doc = await col.find_one({'_id': chat_jid})
            if not doc or not doc.get('groups'):
                return {'ok': False, 'message': 'Você não tem grupos 😔'}
        except Exception:
            logger.exception('group_mentions_list_all_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui listar os grupos 😔'}
        return {'ok': True, 'groups': doc['groups']}
