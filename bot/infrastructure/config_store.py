from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.domain.models.blocked_member import BlockedMember
from bot.domain.models.chat_config import ChatConfig, ChatKey, ChatPolicy
from bot.infrastructure.config_tables import BlockedUserRow, ChatRow, CommandOverrideRow
from bot.infrastructure.database import Database


class SqlConfigStore:
    async def load(self, platform: str, native_id: str) -> ChatConfig:
        async with Database.session() as session:
            chat = await self._find(session, platform, native_id)
            if chat is None:
                return ChatConfig()
            overrides = {override.command_name: override.enabled for override in chat.overrides}
            return ChatConfig(
                policy=ChatPolicy(chat.default_policy),
                overrides=overrides,
                dev_admin=chat.dev_admin,
                blocked=tuple(
                    BlockedMember(key=row.user_key, alt_key=row.alt_key)
                    for row in sorted(chat.blocked, key=lambda row: row.user_key)
                ),
            )

    async def set_override(self, key: ChatKey, command_name: str, *, enabled: bool) -> None:
        async with Database.session() as session:
            chat_id = await self._upsert_chat(session, key)
            # onupdate doesn't fire on a conflict, so updated_at is set by hand.
            await session.execute(
                insert(CommandOverrideRow)
                .values(chat_id=chat_id, command_name=command_name, enabled=enabled)
                .on_conflict_do_update(
                    constraint='uq_override_chat_command',
                    set_={'enabled': enabled, 'updated_at': func.now()},
                )
            )
            await session.commit()

    async def clear_override(self, key: ChatKey, command_name: str) -> None:
        async with Database.session() as session:
            await session.execute(
                delete(CommandOverrideRow).where(
                    CommandOverrideRow.chat_id == self._chat_id(key),
                    CommandOverrideRow.command_name == command_name,
                )
            )
            await session.commit()

    async def set_policy(self, key: ChatKey, policy: ChatPolicy) -> None:
        async with Database.session() as session:
            await self._upsert_chat(session, key, default_policy=policy.value)
            await session.commit()

    async def set_dev_admin(self, key: ChatKey, *, enabled: bool) -> None:
        async with Database.session() as session:
            await self._upsert_chat(session, key, dev_admin=enabled)
            await session.commit()

    async def block_members(self, key: ChatKey, members: Sequence[BlockedMember]) -> None:
        async with Database.session() as session:
            chat_id = await self._upsert_chat(session, key)
            rows = [
                {'chat_id': chat_id, 'user_key': member.key, 'alt_key': member.alt_key}
                for member in members
            ]
            await session.execute(
                insert(BlockedUserRow)
                .values(rows)
                .on_conflict_do_nothing(constraint='uq_blocked_chat_user')
            )
            await session.commit()

    async def unblock_members(self, key: ChatKey, members: Sequence[BlockedMember]) -> None:
        # Either form names the member, so a block set by LID lifts by phone number too.
        keys = set().union(*(member.keys for member in members))
        async with Database.session() as session:
            await session.execute(
                delete(BlockedUserRow).where(
                    BlockedUserRow.chat_id == self._chat_id(key),
                    or_(BlockedUserRow.user_key.in_(keys), BlockedUserRow.alt_key.in_(keys)),
                )
            )
            await session.commit()

    @staticmethod
    def _chat_id(key: ChatKey):
        return (
            select(ChatRow.id)
            .where(ChatRow.platform == key.platform, ChatRow.native_id == key.native_id)
            .scalar_subquery()
        )

    @staticmethod
    async def _find(session: AsyncSession, platform: str, native_id: str) -> ChatRow | None:
        result = await session.execute(
            select(ChatRow)
            .options(selectinload(ChatRow.overrides), selectinload(ChatRow.blocked))
            .where(ChatRow.platform == platform, ChatRow.native_id == native_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _upsert_chat(session: AsyncSession, key: ChatKey, **fields: str | bool) -> UUID:
        result = await session.execute(
            insert(ChatRow)
            .values(platform=key.platform, native_id=key.native_id, type=key.type.value, **fields)
            .on_conflict_do_update(
                constraint='uq_chat_platform_native',
                set_={**fields, 'updated_at': func.now()},
            )
            .returning(ChatRow.id)
        )
        return result.scalar_one()
