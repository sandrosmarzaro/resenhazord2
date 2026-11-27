import json
import uuid
import zlib
from typing import Any, ClassVar

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from bot.settings import Settings

logger = structlog.get_logger()


class ExecutionStore:
    """Execution records in Redis, found again by any reply message they produced.

    One compressed record per command and one pointer per reply, all expiring together.
    Every command writes one, so the retention is short: the Redis plan is 30 MB and
    shared with the agent checkpointer and the inboxes.
    """

    RETENTION_SECONDS: ClassVar[int] = 3 * 86_400
    _RECORD_PREFIX: ClassVar[str] = 'execution'
    _REPLY_PREFIX: ClassVar[str] = 'execution_reply'
    _instance: ClassVar['ExecutionStore | None'] = None

    def __init__(self, redis: Redis | None) -> None:
        self._redis = redis

    @classmethod
    def instance(cls) -> ExecutionStore:
        if cls._instance is None:
            redis_url = Settings().redis_url
            cls._instance = cls(Redis.from_url(redis_url) if redis_url else None)
        return cls._instance

    @classmethod
    def reset(cls, store: ExecutionStore | None = None) -> None:
        cls._instance = store

    async def save(
        self, record: dict[str, Any], platform: str, chat: str, message_ids: list[str]
    ) -> None:
        if self._redis is None or not message_ids:
            return
        record_key = f'{self._RECORD_PREFIX}:{uuid.uuid4().hex}'
        try:
            async with self._redis.pipeline(transaction=False) as pipeline:
                pipeline.set(record_key, self._encode(record), ex=self.RETENTION_SECONDS)
                for message_id in message_ids:
                    reply_key = self._reply_key(platform, chat, message_id)
                    pipeline.set(reply_key, record_key, ex=self.RETENTION_SECONDS)
                await pipeline.execute()
        except RedisError as error:
            # The reply is already out; a missing record only costs a later ,bug.
            logger.warning('execution_record_failed', error=str(error))

    async def find(self, platform: str, chat: str, message_id: str) -> dict[str, Any] | None:
        if self._redis is None:
            return None
        record_key = await self._redis.get(self._reply_key(platform, chat, message_id))
        if record_key is None:
            return None
        encoded = await self._redis.get(record_key)
        return None if encoded is None else json.loads(zlib.decompress(encoded))

    @classmethod
    def _reply_key(cls, platform: str, chat: str, message_id: str) -> str:
        # WhatsApp message ids are only unique within a chat.
        return f'{cls._REPLY_PREFIX}:{platform}:{chat}:{message_id}'

    @staticmethod
    def _encode(record: dict[str, Any]) -> bytes:
        return zlib.compress(json.dumps(record, default=str).encode())
