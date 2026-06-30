from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.domain.models.chat_config import ChatConfig, ChatKey, ChatPolicy
from bot.infrastructure.config_tables import ChatRow, CommandOverrideRow
from bot.infrastructure.database import Database


class SqlConfigStore:
    async def load(self, platform: str, native_id: str) -> ChatConfig:
        async with Database.session() as session:
            chat = await self._find(session, platform, native_id)
            if chat is None:
                return ChatConfig()
            overrides = {override.command_name: override.enabled for override in chat.overrides}
            return ChatConfig(policy=ChatPolicy(chat.default_policy), overrides=overrides)

    async def set_override(self, key: ChatKey, command_name: str, *, enabled: bool) -> None:
        async with Database.session() as session:
            chat = await self._get_or_create(session, key)
            existing = self._override_named(chat, command_name)
            if existing is None:
                override = CommandOverrideRow(command_name=command_name, enabled=enabled)
                chat.overrides.append(override)
            else:
                existing.enabled = enabled
            await session.commit()

    async def clear_override(self, key: ChatKey, command_name: str) -> None:
        async with Database.session() as session:
            chat = await self._find(session, key.platform, key.native_id)
            if chat is None:
                return
            existing = self._override_named(chat, command_name)
            if existing is not None:
                await session.delete(existing)
                await session.commit()

    async def set_policy(self, key: ChatKey, policy: ChatPolicy) -> None:
        async with Database.session() as session:
            chat = await self._get_or_create(session, key)
            chat.default_policy = policy.value
            await session.commit()

    @staticmethod
    def _override_named(chat: ChatRow, command_name: str) -> CommandOverrideRow | None:
        return next((o for o in chat.overrides if o.command_name == command_name), None)

    @staticmethod
    async def _find(session: AsyncSession, platform: str, native_id: str) -> ChatRow | None:
        result = await session.execute(
            select(ChatRow)
            .options(selectinload(ChatRow.overrides))
            .where(ChatRow.platform == platform, ChatRow.native_id == native_id)
        )
        return result.scalar_one_or_none()

    async def _get_or_create(self, session: AsyncSession, key: ChatKey) -> ChatRow:
        chat = await self._find(session, key.platform, key.native_id)
        if chat is not None:
            return chat
        chat = ChatRow(
            platform=key.platform,
            native_id=key.native_id,
            type=key.type.value,
            overrides=[],
        )
        session.add(chat)
        await session.flush()
        return chat
