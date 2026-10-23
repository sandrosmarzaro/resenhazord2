from typing import Protocol


class CommandInboxPort(Protocol):
    async def is_done(self, key: str) -> bool: ...

    async def mark_done(self, key: str) -> None: ...
