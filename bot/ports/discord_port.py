from typing import Protocol

import discord


class DiscordPort(Protocol):
    async def send_message(
        self,
        text: str | None = None,
        *,
        embed: discord.Embed | None = None,
        file: discord.File | None = None,
    ) -> None: ...

    async def defer(self) -> None: ...

    async def send_followup(
        self,
        text: str | None = None,
        *,
        embed: discord.Embed | None = None,
        file: discord.File | None = None,
    ) -> None: ...

    @property
    def is_deferred(self) -> bool: ...
