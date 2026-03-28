import structlog

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class ExitMentionList:
    async def execute(
        self,
        chat_jid: str,
        group_name: str,
        sender_jid: str,
        indices: list[int],
    ) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            has_group = await col.find_one({'_id': chat_jid, 'groups.name': group_name})
            if not has_group:
                return {
                    'ok': False,
                    'message': f'Não existe um grupo com o nome *{group_name}* 😔',
                }

            if not indices:
                await col.update_one(
                    {'_id': chat_jid, 'groups.name': group_name},
                    {'$pull': {'groups.$.participants': sender_jid}},
                )
                return {'ok': True, 'group_name': group_name, 'self_only': True}

            group_doc = await col.find_one(
                {'_id': chat_jid, 'groups.name': group_name},
                projection={'groups.$': 1},
            )
            if not group_doc:
                return {'ok': False, 'message': 'Grupo não encontrado 😔'}
            group_data = group_doc['groups'][0]
            to_remove = [
                group_data['participants'][i - 1]
                for i in indices
                if 0 < i <= len(group_data['participants'])
            ]

            if not to_remove:
                return {
                    'ok': False,
                    'message': 'Nenhum participante encontrado para os índices fornecidos 😔',
                }

            await col.update_one(
                {'_id': chat_jid, 'groups.name': group_name},
                {'$pull': {'groups.$.participants': {'$in': to_remove}}},
            )
        except Exception:
            logger.exception('group_mentions_exit_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui remover os participantes 😔'}
        return {'ok': True, 'group_name': group_name, 'self_only': False}
