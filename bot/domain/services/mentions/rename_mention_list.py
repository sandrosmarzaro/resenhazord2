import structlog

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class RenameMentionList:
    async def execute(self, chat_jid: str, old_name: str, new_name: str) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            has_old = await col.find_one({'_id': chat_jid, 'groups.name': old_name})
            if not has_old:
                return {
                    'ok': False,
                    'message': f'Não existe um grupo com o nome *{old_name}* 😔',
                }

            has_new = await col.find_one({'_id': chat_jid, 'groups.name': new_name})
            if has_new:
                return {
                    'ok': False,
                    'message': f'Já existe um grupo com o nome *{new_name}* 😔',
                }

            await col.update_one(
                {'_id': chat_jid, 'groups.name': old_name},
                {'$set': {'groups.$.name': new_name}},
            )
        except Exception:
            logger.exception('group_mentions_rename_error', chat_jid=chat_jid)
            return {'ok': False, 'message': f'Não consegui renomear o grupo *{old_name}* 😔'}
        return {'ok': True, 'old_name': old_name, 'new_name': new_name}
