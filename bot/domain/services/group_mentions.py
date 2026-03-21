"""Service for managing group mention lists in MongoDB."""

import structlog

from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()

COLLECTION_NAME = 'groups_mentions'


class GroupMentionsService:
    """CRUD operations for group mention lists stored in MongoDB."""

    def _collection(self):
        return MongoDBConnection.collection(COLLECTION_NAME)

    async def create(
        self,
        chat_jid: str,
        sender_jid: str,
        group_name: str,
        mentioned: list[str],
    ) -> dict:
        try:
            col = self._collection()
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

    async def rename(self, chat_jid: str, old_name: str, new_name: str) -> dict:
        try:
            col = self._collection()
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

    async def delete(self, chat_jid: str, group_name: str) -> dict:
        try:
            col = self._collection()
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

    async def list_all(self, chat_jid: str) -> dict:
        try:
            col = self._collection()
            doc = await col.find_one({'_id': chat_jid})
            if not doc or not doc.get('groups'):
                return {'ok': False, 'message': 'Você não tem grupos 😔'}
        except Exception:
            logger.exception('group_mentions_list_all_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui listar os grupos 😔'}
        return {'ok': True, 'groups': doc['groups']}

    async def list_one(self, chat_jid: str, group_name: str) -> dict:
        try:
            col = self._collection()
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

    async def add(
        self,
        chat_jid: str,
        group_name: str,
        sender_jid: str,
        participants: list[str],
    ) -> dict:
        try:
            col = self._collection()
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

    async def exit(
        self,
        chat_jid: str,
        group_name: str,
        sender_jid: str,
        indices: list[int],
    ) -> dict:
        try:
            col = self._collection()
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

    async def mention(self, chat_jid: str, group_name: str) -> dict:
        try:
            col = self._collection()
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
            logger.exception('group_mentions_mention_error', chat_jid=chat_jid)
            return {'ok': False, 'message': 'Não consegui marcar os participantes 😔'}
        return {'ok': True, 'participants': group['participants']}
