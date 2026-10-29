import time
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from bot.domain.models.command_data import CommandData
from bot.infrastructure.metrics import record_agent_budget_rejection, record_agent_tokens

logger = structlog.get_logger()


@dataclass(frozen=True)
class TokenBudgetPolicy:
    user_per_day: int
    group_per_day: int
    enforce: bool
    owners: frozenset[str]


@dataclass(frozen=True)
class _Bucket:
    _SECONDS_PER_DAY: ClassVar[int] = 86_400

    scope: str
    key: str
    per_day: int

    @property
    def per_second(self) -> float:
        return self.per_day / self._SECONDS_PER_DAY


class TokenBudget:
    """One token bucket per sender and one per group, so a busy chat cannot drain the
    free-tier LLM quotas everyone shares. A bucket holds a day's budget and refills
    continuously. A call is debited after it, when the provider reports its usage, so
    a balance can dip below zero and then blocks until it refills."""

    TIMEZONE: ClassVar[ZoneInfo] = ZoneInfo('America/Sao_Paulo')
    _KEY_PREFIX: ClassVar[str] = 'agent_budget'
    # Refills the bucket up to now, then debits the cost. The key expires when the
    # bucket would be full again, since a missing bucket reads as full.
    _SETTLE: ClassVar[str] = """
local capacity, rate = tonumber(ARGV[1]), tonumber(ARGV[2])
local now, cost = tonumber(ARGV[3]), tonumber(ARGV[4])
local bucket = redis.call('HMGET', KEYS[1], 'balance', 'at')
local balance = tonumber(bucket[1]) or capacity
local at = tonumber(bucket[2]) or now
balance = math.min(capacity, balance + (now - at) * rate) - cost
redis.call('HSET', KEYS[1], 'balance', balance, 'at', now)
redis.call('EXPIRE', KEYS[1], math.ceil((capacity - balance) / rate))
return tostring(balance)
"""

    def __init__(self, redis: Redis, policy: TokenBudgetPolicy) -> None:
        self._policy = policy
        self._settle = redis.register_script(self._SETTLE)

    @classmethod
    def from_url(cls, redis_url: str, policy: TokenBudgetPolicy) -> TokenBudget:
        return cls(Redis.from_url(redis_url), policy)

    async def refill_at(self, data: CommandData) -> datetime | None:
        now = time.time()
        wait = 0.0
        for bucket, balance in await self._settle_all(data, 0, now):
            if balance > 0:
                continue
            logger.info('agent_over_budget', scope=bucket.scope, enforced=self._policy.enforce)
            record_agent_budget_rejection(bucket.scope, enforced=self._policy.enforce)
            # The next call needs a positive balance, one token above zero.
            wait = max(wait, (1 - balance) / bucket.per_second)
        if not wait or not self._policy.enforce:
            return None
        return datetime.fromtimestamp(now + wait, self.TIMEZONE)

    async def spend(self, data: CommandData, tokens: int) -> None:
        record_agent_tokens(tokens)
        await self._settle_all(data, tokens, time.time())

    async def _settle_all(
        self, data: CommandData, cost: int, now: float
    ) -> list[tuple[_Bucket, float]]:
        try:
            return [
                (bucket, await self._settle_one(bucket, cost, now))
                for bucket in self._buckets(data)
            ]
        except RedisError as error:
            # A lost budget beats a silent bot: fail open.
            logger.warning('agent_budget_unavailable', error=str(error))
            return []

    async def _settle_one(self, bucket: _Bucket, cost: int, now: float) -> float:
        args = [bucket.per_day, bucket.per_second, now, cost]
        return float(await self._settle(keys=[bucket.key], args=args))

    def _buckets(self, data: CommandData) -> list[_Bucket]:
        # sender_jid carries the phone-number JID even in LID-addressed groups.
        if data.sender_jid in self._policy.owners:
            return []
        key = f'{self._KEY_PREFIX}:user:{data.sender_jid}'
        buckets = [_Bucket('user', key, self._policy.user_per_day)]
        if data.is_group:
            key = f'{self._KEY_PREFIX}:group:{data.jid}'
            buckets.append(_Bucket('group', key, self._policy.group_per_day))
        return buckets
