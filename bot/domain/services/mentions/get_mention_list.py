import structlog

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class GetMentionList:
    async def execute(self, chat_jid: str, group_name: str) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            doc = await col.find_one({'_id': chat_jid})
            if not doc or not doc.get('groups'):
                return {'ok': False, 'message': 'Você não tem grupos 😔'}

            group = next((g for g in doc['groups'] if g['name'] == group_name), None)
            if not group:
                return {
                    'ok': False,
                    'message': f'Não existe um grupo com o nome *{group_name}* 😔',
                }
        except Exception:
            logger.exception('group_mentions_list_one_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui listar os grupos 😔'}
        return {'ok': True, 'name': group['name'], 'participants': group['participants']}
