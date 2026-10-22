from typing import Protocol


class AgentRateLimiterPort(Protocol):
    async def allow(self, conversation: str) -> bool: ...
