import json
from typing import Any, ClassVar

import structlog

from bot.domain.exceptions import DownloadError, ExternalServiceError
from bot.infrastructure.metrics import record_dlq, record_retry
from bot.ports.broker_port import BrokerPort, DeliveryRejectedError

logger = structlog.get_logger()


class RetryRouter:
    MAX_ATTEMPTS: ClassVar[int] = 3
    DOWNLOAD_MAX_ATTEMPTS: ClassVar[int] = 1

    def __init__(self, broker: BrokerPort, dlq_queue: str) -> None:
        self._broker = broker
        self._dlq_queue = dlq_queue

    async def route(
        self, envelope: dict[str, Any], error: ExternalServiceError, attempt: int
    ) -> None:
        """Reject the delivery into the retry ladder, or dead-letter the envelope."""
        if attempt < self._max_attempts(error):
            logger.warning('command_retry_scheduled', attempts=attempt, error=str(error))
            record_retry()
            # The broker dead-letters the rejection to the ladder step for this attempt.
            raise DeliveryRejectedError from error
        # A permanently-failed download (blocked/private/unsupported URL) is an
        # expected user outcome already answered with a friendly reply, not an
        # incident — log it below Sentry's error capture. A non-download error
        # exhausting the full ladder is a real outage and stays at error level.
        log = logger.warning if isinstance(error, DownloadError) else logger.error
        log('command_retries_exhausted', attempts=attempt, error=str(error))
        record_dlq()
        await self._broker.publish(self._dlq_queue, json.dumps(envelope).encode())

    @classmethod
    def _max_attempts(cls, error: ExternalServiceError) -> int:
        # yt-dlp failures are usually permanent, so they skip the multi-minute ladder.
        return cls.DOWNLOAD_MAX_ATTEMPTS if isinstance(error, DownloadError) else cls.MAX_ATTEMPTS
