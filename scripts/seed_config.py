"""Seed per-group config from existing settings. Idempotent; safe to re-run.

Run once at cutover (ADR 0012, PRD §11):

    uv run task seed:config

Preserves the Telegram NSFW allow-list (enables the +18 commands for those chats)
and marks the resenha group CURATED. Every other chat keeps the safe default.
"""

import asyncio
from collections.abc import Iterable

import structlog

from bot.application.command_registry import CommandRegistry
from bot.application.register_commands import register_all_commands
from bot.domain.commands.base import CommandScope
from bot.domain.models.chat_config import ChatKey, ChatPolicy, ChatType
from bot.infrastructure.config_store import SqlConfigStore
from bot.infrastructure.database import Database
from bot.ports.config_store_port import ConfigStorePort
from bot.settings import Settings

logger = structlog.get_logger()


async def seed(
    store: ConfigStorePort,
    nsfw_command_names: list[str],
    telegram_nsfw_chat_ids: Iterable[int],
    resenha_jid: str,
) -> None:
    for chat_id in telegram_nsfw_chat_ids:
        key = ChatKey(platform='telegram', native_id=str(chat_id), type=ChatType.GROUP)
        for name in nsfw_command_names:
            await store.set_override(key, name, enabled=True)
        logger.info('seeded_telegram_nsfw', chat_id=chat_id, commands=len(nsfw_command_names))

    if resenha_jid:
        key = ChatKey(platform='whatsapp', native_id=resenha_jid, type=ChatType.GROUP)
        await store.set_policy(key, ChatPolicy.CURATED)
        logger.info('seeded_resenha_curated', native_id=resenha_jid)


def _nsfw_command_names(registry: CommandRegistry) -> list[str]:
    return [
        command.config.name
        for command in registry.get_all()
        if command.config.scope == CommandScope.NSFW
    ]


def _parse_chat_ids(raw: str) -> list[int]:
    return [int(part) for part in raw.split(',') if part.strip()]


async def main(settings: Settings) -> None:
    register_all_commands(settings)
    Database.configure(settings.database_url)
    try:
        await seed(
            SqlConfigStore(),
            _nsfw_command_names(CommandRegistry.instance()),
            _parse_chat_ids(settings.telegram_nsfw_chat_ids),
            settings.resenha_jid,
        )
    finally:
        await Database.close()


if __name__ == '__main__':
    asyncio.run(main(Settings()))
