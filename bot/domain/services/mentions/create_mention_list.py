import structlog

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
            has_group = await col.find_one({'_id': chat_jid, 'groups.name': group_name})
            if has_group:
                return {
                    'ok': False,
                    'message': f'Já existe um grupo com o nome *{group_name}* 😔',
                }

            participants = [sender_jid, *mentioned]
            has_doc = await col.find_one({'_id': chat_jid})
            if not has_doc:
                await col.insert_one(
                    {
                        '_id': chat_jid,
                        'groups': [{'name': group_name, 'participants': participants}],
                    }
                )
            else:
                await col.update_one(
                    {'_id': chat_jid},
                    {'$push': {'groups': {'name': group_name, 'participants': participants}}},
                )
        except Exception:
            logger.exception('group_mentions_create_error', chat_jid=chat_jid)
            return {'ok': False, 'message': f'Não consegui criar o grupo *{group_name}* 😔'}
        return {'ok': True, 'group_name': group_name}
