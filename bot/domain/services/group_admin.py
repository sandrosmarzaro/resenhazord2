from bot.adapters.whatsapp.port import WhatsAppPort
from bot.domain.commands.base import Platform
from bot.domain.models.command_data import CommandData


class GroupAdminService:
    async def is_authorized(self, data: CommandData, whatsapp: WhatsAppPort | None) -> bool:
        if not data.is_group:
            return True
        if data.is_admin is not None:
            return data.is_admin
        if data.platform != Platform.WHATSAPP or whatsapp is None:
            return False
        metadata = await whatsapp.group_metadata(data.jid)
        sender = data.participant or data.sender_jid
        return self._is_admin(metadata['participants'], sender)

    @staticmethod
    def _is_admin(participants: list[dict], sender: str) -> bool:
        entry = next((member for member in participants if member['id'] == sender), None)
        return bool(entry and entry.get('admin'))
