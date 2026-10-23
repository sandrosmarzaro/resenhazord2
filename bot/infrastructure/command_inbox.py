from typing import ClassVar

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger()


class RedisCommandInbox:
    """Remembers answered commands so a broker redelivery (ADR 0001) is not answered twice."""

    # Redelivery follows a crash within minutes; a day covers a long outage too.
    RETENTION_SECONDS: ClassVar[int] = 86_400
    _KEY_PREFIX: ClassVar[str] = 'command_done'

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @classmethod
    def from_url(cls, redis_url: str) -> RedisCommandInbox:
        return cls(Redis.from_url(redis_url))

    async def is_done(self, key: str) -> bool:
        try:
            return bool(await self._redis.exists(f'{self._KEY_PREFIX}:{key}'))
        except RedisError as error:
            # A duplicate reply beats a dropped command: fail open.
            logger.warning('command_inbox_unavailable', error=str(error))
            return False

    async def mark_done(self, key: str) -> None:
        try:
            await self._redis.set(f'{self._KEY_PREFIX}:{key}', 1, ex=self.RETENTION_SECONDS)
        except RedisError as error:
            logger.warning('command_inbox_unavailable', error=str(error))
