from datetime import datetime
from typing import Protocol

from bot.domain.models.command_data import CommandData


class TokenBudgetPort(Protocol):
    async def refill_at(self, data: CommandData) -> datetime | None: ...

    async def spend(self, data: CommandData, tokens: int) -> None: ...
