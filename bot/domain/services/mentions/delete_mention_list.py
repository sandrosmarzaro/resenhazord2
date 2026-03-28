import structlog

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class DeleteMentionList:
    async def execute(self, chat_jid: str, group_name: str) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            has_group = await col.find_one({'_id': chat_jid, 'groups.name': group_name})
            if not has_group:
                return {
                    'ok': False,
                    'message': f'Não existe um grupo com o nome *{group_name}* 😔',
                }

            await col.update_one(
                {'_id': chat_jid},
                {'$pull': {'groups': {'name': group_name}}},
            )
        except Exception:
            logger.exception('group_mentions_delete_error', chat_jid=chat_jid)
            return {'ok': False, 'message': f'Não consegui deletar o grupo *{group_name}* 😔'}
        return {'ok': True, 'group_name': group_name}
