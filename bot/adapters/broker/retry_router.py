import json
from typing import Any, ClassVar

import structlog

from bot.domain.exceptions import DownloadError, ExternalServiceError
from bot.infrastructure.metrics import record_dlq, record_retry
from bot.ports.broker_port import BrokerPort

logger = structlog.get_logger()


class RetryRouter:
    MAX_ATTEMPTS: ClassVar[int] = 3
    DOWNLOAD_MAX_ATTEMPTS: ClassVar[int] = 1

    def __init__(self, broker: BrokerPort, retry_queue: str, dlq_queue: str) -> None:
        self._broker = broker
        self._retry_queue = retry_queue
        self._dlq_queue = dlq_queue

    async def route(self, envelope: dict[str, Any], error: ExternalServiceError) -> bool:
        """Park the envelope for a retry, or dead-letter it; True once dead-lettered."""
        attempts = envelope.get('attempts', 0) + 1
        if attempts < self._max_attempts(error):
            envelope['attempts'] = attempts
            await self._broker.publish(self._retry_queue, json.dumps(envelope).encode())
            logger.warning('command_retry_scheduled', attempts=attempts, error=str(error))
            record_retry()
            return False
        # A permanently-failed download (blocked/private/unsupported URL) is an
        # expected user outcome already answered with a friendly reply, not an
        # incident — log it below Sentry's error capture. A non-download error
        # exhausting the full ladder is a real outage and stays at error level.
        log = logger.warning if isinstance(error, DownloadError) else logger.error
        log('command_retries_exhausted', attempts=attempts, error=str(error))
        record_dlq()
        await self._broker.publish(self._dlq_queue, json.dumps(envelope).encode())
        return True

    @classmethod
    def _max_attempts(cls, error: ExternalServiceError) -> int:
        # yt-dlp failures are usually permanent, so they skip the multi-minute ladder.
        return cls.DOWNLOAD_MAX_ATTEMPTS if isinstance(error, DownloadError) else cls.MAX_ATTEMPTS
