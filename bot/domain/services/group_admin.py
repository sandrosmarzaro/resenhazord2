import structlog

from bot.adapters.whatsapp.port import WhatsAppPort
from bot.domain.commands.base import Platform
from bot.domain.dev_key import DevKey
from bot.domain.models.command_data import CommandData
from bot.domain.services.dev_list import DevListService
from bot.infrastructure.cached_config_store import CachedConfigStore
from bot.ports.config_store_port import ConfigStorePort

logger = structlog.get_logger()


class GroupAdminService:
    def __init__(
        self,
        dev_list: DevListService | None = None,
        store: ConfigStorePort | None = None,
    ) -> None:
        self._dev_list = dev_list or DevListService()
        self._store = store or CachedConfigStore.instance()

    async def is_authorized(self, data: CommandData, whatsapp: WhatsAppPort | None) -> bool:
        if await self.is_admin(data, whatsapp):
            return True
        return await self._is_trusted_dev(data)

    async def is_admin(self, data: CommandData, whatsapp: WhatsAppPort | None) -> bool:
        if not data.is_group:
            return True
        if data.is_admin is not None:
            return data.is_admin
        if data.platform != Platform.WHATSAPP or whatsapp is None:
            return False
        metadata = await whatsapp.group_metadata(data.jid)
        return self.is_sender_admin(data, metadata['participants'])

    @staticmethod
    def is_sender_admin(data: CommandData, participants: list[dict]) -> bool:
        # For callers that already hold the group's participants, so the check costs no
        # second metadata round trip.
        if data.is_admin is not None:
            return data.is_admin
        sender = data.participant or data.sender_jid
        entry = next((member for member in participants if member['id'] == sender), None)
        return bool(entry and entry.get('admin'))

    async def _is_trusted_dev(self, data: CommandData) -> bool:
        # The chat flag is a cache hit, so it goes before the Mongo dev lookup.
        config = await self._store.load(data.platform or '', data.jid)
        if not config.dev_admin:
            return False
        sender = DevKey.of(data)
        if not await self._dev_list.is_dev(sender):
            return False
        logger.info('dev_admin_bypass', chat=data.jid, dev=sender)
        return True
