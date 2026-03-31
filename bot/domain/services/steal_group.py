import structlog

from bot.adapters.whatsapp.port import WhatsAppPort
from bot.data.roman_numerals import to_roman
from bot.infrastructure.http_client import HttpClient
from bot.infrastructure.mongodb import MongoDBConnection

logger = structlog.get_logger()


class StealGroupService:
    COLONY_EMOJI = '🐮🎣🍆'
    COLONY_DESCRIPTION = 'Este grupo pertece agora a Resenha 🔒'
    NOTIFICATION_EXPIRATION = 86400
    LOREMFLICKR_URL = 'https://loremflickr.com/900/900/'

    def __init__(self, whatsapp: WhatsAppPort, resenhazord2_jid: str, resenha_jid: str) -> None:
        self._whatsapp = whatsapp
        self._resenhazord2_jid = resenhazord2_jid
        self._resenha_jid = resenha_jid

    async def run(self, data: dict) -> None:
        if data.get('action') != 'promote':
            return

        bot_promoted = any(
            p.get('id') == self._resenhazord2_jid for p in data.get('participants', [])
        )
        if not bot_promoted:
            return

        group_jid = data['id']
        try:
            await self._steal(group_jid)
        except Exception:
            logger.exception('steal_group_error', group_jid=group_jid)

    async def _steal(self, group_jid: str) -> None:
        metadata = await self._whatsapp.group_metadata(group_jid)
        participants = metadata.get('participants', [])

        admin_jids = [
            p['id'] for p in participants if p.get('admin') and p['id'] != self._resenhazord2_jid
        ]

        owner_jid = metadata.get('ownerPn', '')
        if owner_jid in admin_jids:
            return

        await self._whatsapp.group_participants_update(group_jid, admin_jids, 'demote')

        colony_number = await self._next_colony_number()
        roman = to_roman(colony_number)

        subject = metadata.get('subject', '')
        desc = metadata.get('desc', '')

        await self._whatsapp.group_update_subject(
            group_jid, f'Colônia da Resenha {roman} {self.COLONY_EMOJI}'
        )
        await self._whatsapp.send_message(
            self._resenha_jid,
            {'text': f'Colônia obtida!\n\n*{subject}\n*{desc}'},
            {'ephemeralExpiration': self.NOTIFICATION_EXPIRATION},
        )
        await self._whatsapp.group_update_description(group_jid, self.COLONY_DESCRIPTION)

        image_buffer = await HttpClient.get_buffer(self.LOREMFLICKR_URL)
        await self._whatsapp.update_profile_picture(group_jid, image_buffer)

        logger.debug('group_stolen', group_jid=group_jid, colony=roman)

    @staticmethod
    async def _next_colony_number() -> int:
        collection = MongoDBConnection.collection('colonias')
        result = await collection.find_one_and_update(
            {'_id': 'counter'},
            {'$inc': {'number': 1}},
            return_document=True,
            upsert=True,
        )
        return result['number']
