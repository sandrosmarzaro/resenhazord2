import structlog

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class AddToMentionList:
    async def execute(
        self,
        chat_jid: str,
        group_name: str,
        sender_jid: str,
        participants: list[str],
    ) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            has_group = await col.find_one({'_id': chat_jid, 'groups.name': group_name})
            if not has_group:
                return {
                    'ok': False,
                    'message': f'Não existe um grupo com o nome *{group_name}* 😔',
                }

            if not participants:
                await col.update_one(
                    {'_id': chat_jid, 'groups.name': group_name},
                    {'$addToSet': {'groups.$.participants': sender_jid}},
                )
                return {'ok': True, 'group_name': group_name, 'self_only': True}

            await col.update_one(
                {'_id': chat_jid, 'groups.name': group_name},
                {'$addToSet': {'groups.$.participants': {'$each': participants}}},
            )
        except Exception:
            logger.exception('group_mentions_add_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui adicionar os participantes 😔'}
        return {'ok': True, 'group_name': group_name, 'self_only': False}
