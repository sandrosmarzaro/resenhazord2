from typing import ClassVar

import sentry_sdk
import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger()


class AgentRateLimiter:
    """Caps agent turns per conversation so a bot on the other end cannot loop with ours."""

    MAX_TURNS: ClassVar[int] = 5
    WINDOW_SECONDS: ClassVar[int] = 120
    _KEY_PREFIX: ClassVar[str] = 'agent_turns'

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @classmethod
    def from_url(cls, redis_url: str) -> AgentRateLimiter:
        return cls(Redis.from_url(redis_url))

    async def allow(self, conversation: str) -> bool:
        key = f'{self._KEY_PREFIX}:{conversation}'
        try:
            async with self._redis.pipeline() as pipeline:
                # SET NX opens the window with its TTL; INCR keeps that TTL.
                pipeline.set(key, 0, ex=self.WINDOW_SECONDS, nx=True)
                pipeline.incr(key)
                _, turns = await pipeline.execute()
        except RedisError as error:
            # A lost limiter beats a silent bot: fail open.
            logger.warning('agent_rate_limit_unavailable', error=str(error))
            return True
        if turns == self.MAX_TURNS + 1:
            sentry_sdk.capture_message('agent_rate_limited', level='warning')
        return turns <= self.MAX_TURNS
