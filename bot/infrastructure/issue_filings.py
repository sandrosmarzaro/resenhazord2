from typing import ClassVar

from redis.asyncio import Redis


class IssueFilings:
    """One issue per ,bug message, so a broker redelivery (ADR 0001) doesn't file twice.

    The claim is taken before the GitHub call and settled with the issue's URL after
    it. A failed call releases it, so the retry files the issue once.
    """

    # Redelivery follows a crash within minutes; a day covers a long outage too.
    RETENTION_SECONDS: ClassVar[int] = 86_400
    IN_PROGRESS: ClassVar[str] = 'in_progress'
    _KEY_PREFIX: ClassVar[str] = 'bug_issue'

    def __init__(self, redis: Redis | None) -> None:
        # Without Redis there is no execution record to file from, so no guard is lost.
        self._redis = redis

    async def claim(self, key: str) -> str | None:
        if self._redis is None:
            return None
        name = f'{self._KEY_PREFIX}:{key}'
        if await self._redis.set(name, self.IN_PROGRESS, nx=True, ex=self.RETENTION_SECONDS):
            return None
        # Expired between the two calls, it still reads as taken: the next try files it.
        existing = await self._redis.get(name) or self.IN_PROGRESS.encode()
        return existing.decode()

    async def settle(self, key: str, url: str) -> None:
        if self._redis is None:
            return
        await self._redis.set(f'{self._KEY_PREFIX}:{key}', url, ex=self.RETENTION_SECONDS)

    async def release(self, key: str) -> None:
        if self._redis is None:
            return
        await self._redis.delete(f'{self._KEY_PREFIX}:{key}')
