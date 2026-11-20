from typing import ClassVar

from bot.domain.commands.base import Platform
from bot.domain.models.command_data import CommandData


class DevKey:
    _NAMESPACED_PLATFORMS: ClassVar[frozenset[Platform]] = frozenset(
        {Platform.DISCORD, Platform.TELEGRAM}
    )

    @classmethod
    def of(cls, data: CommandData) -> str:
        # Discord and Telegram send the bare user id. Namespaced, it can't be read as a
        # WhatsApp number or LID, and it matches the discord:<id> that ,dev add stores.
        if data.platform in cls._NAMESPACED_PLATFORMS:
            return f'{data.platform}:{data.sender_jid}'
        return data.sender_jid
