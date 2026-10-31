import structlog

from bot.domain.jid import normalize_jid, normalize_jids
from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'
GROUP_NAME_FIELD = 'groups.name'


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
            added = (
                {'$each': normalize_jids(participants)}
                if participants
                else normalize_jid(sender_jid)
            )
            result = await col.update_one(
                {'_id': chat_jid, GROUP_NAME_FIELD: group_name},
                {'$addToSet': {'groups.$.participants': added}},
            )
            if not result.matched_count:
                return {
                    'ok': False,
                    'message': f'Não existe um grupo com o nome *{group_name}* 😔',
                }
        except Exception:
            logger.exception('group_mentions_add_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui adicionar os participantes 😔'}
        return {'ok': True, 'group_name': group_name, 'self_only': not participants}
