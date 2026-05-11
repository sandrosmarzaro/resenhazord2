import structlog

from bot.domain.jid import normalize_jid
from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'
GROUP_NAME_FIELD = 'groups.name'


def _matching_participants(sender_jid: str, participants: list[str]) -> list[str]:
    normalized_sender = normalize_jid(sender_jid)
    return [p for p in participants if normalize_jid(p) == normalized_sender]


def _participants_by_indices(participants: list[str], indices: list[int]) -> list[str]:
    return [participants[i - 1] for i in indices if 0 < i <= len(participants)]


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

            if not indices:
                stored_jids = _matching_participants(sender_jid, participants)
                if not stored_jids:
                    return {
                        'ok': False,
                        'message': f'Você não está no grupo *{group_name}* 😔',
                    }

                await col.update_one(
                    {'_id': chat_jid, GROUP_NAME_FIELD: group_name},
                    {'$pull': {'groups.$.participants': {'$in': stored_jids}}},
                )
                return {'ok': True, 'group_name': group_name, 'self_only': True}

            to_remove = _participants_by_indices(participants, indices)

            if not to_remove:
                return {
                    'ok': False,
                    'message': 'Nenhum participante encontrado para os índices fornecidos 😔',
                }

            await col.update_one(
                {'_id': chat_jid, GROUP_NAME_FIELD: group_name},
                {'$pull': {'groups.$.participants': {'$in': to_remove}}},
            )
        except Exception:
            logger.exception('group_mentions_exit_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui remover os participantes 😔'}
        return {'ok': True, 'group_name': group_name, 'self_only': False}
