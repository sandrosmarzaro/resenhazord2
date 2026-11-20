from collections.abc import Awaitable, Callable
from typing import ClassVar

from bot.adapters.whatsapp.port import WhatsAppPort
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Platform
from bot.domain.jid import normalize_jids, strip_jid
from bot.domain.models.blocked_member import BlockedMember
from bot.domain.models.chat_config import ChatKey, ChatType
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.cached_config_store import CachedConfigStore
from bot.ports.config_store_port import ConfigStorePort

Handler = Callable[[CommandData, WhatsAppPort], Awaitable[BotMessage]]


class MemberBlocks:
    VERBS: ClassVar[frozenset[str]] = frozenset({'bloquear', 'desbloquear', 'bloqueados'})
    _UNSUPPORTED: ClassVar[str] = (
        '🚧 Por enquanto só dá pra bloquear membros em grupos do WhatsApp.'
    )
    _NO_TARGET: ClassVar[str] = '❓ Marque quem bloquear ou liberar: *,config bloquear @fulano*.'
    _ADMIN_REFUSED: ClassVar[str] = '🙅 Admin não pode ser bloqueado.'
    _BLOCKED: ClassVar[str] = '🚫 {mentions} não pode mais usar o bot neste grupo.'
    _UNBLOCKED: ClassVar[str] = '✅ {mentions} liberado.'
    _LISTED: ClassVar[str] = 'Bloqueados neste grupo: {mentions}'
    _NOBODY: ClassVar[str] = 'Ninguém bloqueado neste grupo. ✅'

    def __init__(self, store: ConfigStorePort | None = None) -> None:
        self._store = store or CachedConfigStore.instance()
        self._verbs: dict[str, Handler] = {
            'bloquear': self._block,
            'desbloquear': self._unblock,
            'bloqueados': self._list,
        }

    async def apply(
        self, data: CommandData, verb: str, whatsapp: WhatsAppPort | None
    ) -> BotMessage:
        # Discord and Telegram mentions don't reach the core as user ids yet, so only a
        # WhatsApp group can name whom to block.
        is_whatsapp = (data.platform or Platform.WHATSAPP) == Platform.WHATSAPP
        if whatsapp is None or not data.is_group or not is_whatsapp:
            return Reply.to(data).text(self._UNSUPPORTED)
        return await self._verbs[verb](data, whatsapp)

    async def _block(self, data: CommandData, whatsapp: WhatsAppPort) -> BotMessage:
        mentioned = normalize_jids(data.mentioned_jids)
        if not mentioned:
            return Reply.to(data).text(self._NO_TARGET)
        metadata = await whatsapp.group_metadata(data.jid)
        entries = [self._entry(metadata['participants'], jid) for jid in mentioned]
        if any(entry.get('admin') for entry in entries):
            return Reply.to(data).text(self._ADMIN_REFUSED)
        members = [BlockedMember.of_participant(entry) for entry in entries]
        await self._store.block_members(self._key(data), members)
        return self._mentioning(data, self._BLOCKED, mentioned)

    async def _unblock(self, data: CommandData, _whatsapp: WhatsAppPort) -> BotMessage:
        # The store lifts a member by either form, so the mention needs no metadata lookup.
        mentioned = normalize_jids(data.mentioned_jids)
        if not mentioned:
            return Reply.to(data).text(self._NO_TARGET)
        members = [BlockedMember(key=jid) for jid in mentioned]
        await self._store.unblock_members(self._key(data), members)
        return self._mentioning(data, self._UNBLOCKED, mentioned)

    async def _list(self, data: CommandData, _whatsapp: WhatsAppPort) -> BotMessage:
        config = await self._store.load(data.platform or '', data.jid)
        keys = [member.key for member in config.blocked]
        if not keys:
            return Reply.to(data).text(self._NOBODY)
        return self._mentioning(data, self._LISTED, keys)

    @staticmethod
    def _entry(participants: list[dict], jid: str) -> dict:
        # A member who already left has no entry, so the mention is all there is to store.
        matches = (p for p in participants if jid in BlockedMember.of_participant(p).keys)
        return next(matches, {'id': jid})

    @staticmethod
    def _mentioning(data: CommandData, template: str, jids: list[str]) -> BotMessage:
        mentions = ', '.join(f'@{strip_jid(jid)}' for jid in jids)
        return Reply.to(data).text_with(template.format(mentions=mentions), jids)

    @staticmethod
    def _key(data: CommandData) -> ChatKey:
        return ChatKey(platform=data.platform or '', native_id=data.jid, type=ChatType.GROUP)
