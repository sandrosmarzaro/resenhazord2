import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import ClassVar

import structlog

logger = structlog.get_logger()

type Shutdown = Callable[[], Awaitable[None]]
type Connect = Callable[[], Awaitable[Shutdown]]
type PermanentFailures = tuple[type[Exception], ...]


class PlatformStatus(StrEnum):
    STARTING = 'starting'
    RETRYING = 'retrying'
    UP = 'up'
    FAILED = 'failed'


class PlatformSupervisor:
    """Connects each chat platform in its own task, so one failing never stops the others."""

    INITIAL_BACKOFF_SECONDS: ClassVar[float] = 5.0
    MAX_BACKOFF_SECONDS: ClassVar[float] = 300.0

    def __init__(self) -> None:
        self._statuses: dict[str, PlatformStatus] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._shutdowns: list[Shutdown] = []

    def start(
        self, name: str, connect: Connect, permanent: PermanentFailures = ()
    ) -> asyncio.Task[None]:
        self._statuses[name] = PlatformStatus.STARTING
        task = asyncio.create_task(self._supervise(name, connect, permanent))
        self._tasks.append(task)
        return task

    def statuses(self) -> dict[str, PlatformStatus]:
        return dict(self._statuses)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for shutdown in self._shutdowns:
            await shutdown()

    async def _supervise(self, name: str, connect: Connect, permanent: PermanentFailures) -> None:
        backoff = self.INITIAL_BACKOFF_SECONDS
        while self._statuses[name] not in (PlatformStatus.UP, PlatformStatus.FAILED):
            await self._attempt(name, connect, permanent, backoff)
            backoff = min(backoff * 2, self.MAX_BACKOFF_SECONDS)

    async def _attempt(
        self, name: str, connect: Connect, permanent: PermanentFailures, backoff: float
    ) -> None:
        try:
            self._shutdowns.append(await connect())
        except permanent:
            self._statuses[name] = PlatformStatus.FAILED
            logger.exception('platform_failed', platform=name)
            return
        except Exception as error:  # noqa: BLE001
            self._statuses[name] = PlatformStatus.RETRYING
            logger.warning('platform_retrying', platform=name, error=str(error), retry_in=backoff)
            await asyncio.sleep(backoff)
            return
        self._statuses[name] = PlatformStatus.UP
        logger.info('platform_up', platform=name)
