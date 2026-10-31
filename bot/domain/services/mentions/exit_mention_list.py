import structlog
from motor.motor_asyncio import AsyncIOMotorCollection

from bot.domain.jid import normalize_jid
from bot.domain.models.removal_targets import RemovalTargets
from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'
GROUP_NAME_FIELD = 'groups.name'


def _matching_participants(sender_jid: str, participants: list[str]) -> list[str]:
    normalized_sender = normalize_jid(sender_jid)
    return [p for p in participants if normalize_jid(p) == normalized_sender]


class ExitMentionList:
    async def execute(
        self,
        chat_jid: str,
        group_name: str,
        sender_jid: str,
        targets: RemovalTargets,
    ) -> dict:
        try:
            col = MongoDBConnection.collection(COLLECTION_NAME)
            group_doc = await col.find_one(
                {'_id': chat_jid, GROUP_NAME_FIELD: group_name},
                projection={'groups.$': 1},
            )
            if not group_doc:
                return {
                    'ok': False,
                    'message': f'Não existe um grupo com o nome *{group_name}* 😔',
                }
            participants = group_doc['groups'][0]['participants']

            is_self_exit = targets.is_self_exit
            to_remove = (
                _matching_participants(sender_jid, participants)
                if is_self_exit
                else targets.resolve(participants)
            )
            if not await self._pull(col, chat_jid, group_name, to_remove):
                message = (
                    f'Você não está no grupo *{group_name}* 😔'
                    if is_self_exit
                    else 'Nenhum participante encontrado para remover 😔'
                )
                return {'ok': False, 'message': message}
        except Exception:
            logger.exception('group_mentions_exit_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui remover os participantes 😔'}
        return {'ok': True, 'group_name': group_name, 'self_only': is_self_exit}

    @staticmethod
    async def _pull(
        col: AsyncIOMotorCollection, chat_jid: str, group_name: str, to_remove: list[str]
    ) -> bool:
        if not to_remove:
            return False
        # The list above can be stale by now, so only the write says what was removed.
        result = await col.update_one(
            {'_id': chat_jid, GROUP_NAME_FIELD: group_name},
            {'$pull': {'groups.$.participants': {'$in': to_remove}}},
        )
        return result.modified_count > 0
