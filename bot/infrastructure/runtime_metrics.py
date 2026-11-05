"""Saturation of the core process itself: memory, CPU and event-loop lag.

The node exporter sees the whole VM; these see the bot. Loop lag is the one
that explains a slow command with no slow span: CPU work left on the event
loop holds every other command and heartbeat back by that much.
"""

import asyncio
import os
import resource
from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from opentelemetry.metrics import CallbackOptions, Meter, Observation


def register_process_gauges(meter: Meter) -> None:
    meter.create_observable_gauge(
        'process.memory.rss',
        callbacks=[_resident_memory],
        unit='By',
        description='Resident memory of the bot process',
    )
    meter.create_observable_counter(
        'process.cpu.time',
        callbacks=[_cpu_time],
        unit='s',
        description='CPU time the bot process spent, user plus system',
    )


def _resident_memory(_options: CallbackOptions) -> Iterable[Observation]:
    # statm's second field is the resident set, in pages.
    pages = int(Path('/proc/self/statm').read_text().split()[1])
    yield Observation(pages * os.sysconf('SC_PAGE_SIZE'))


def _cpu_time(_options: CallbackOptions) -> Iterable[Observation]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    yield Observation(usage.ru_utime + usage.ru_stime)


class LoopLagMonitor:
    INTERVAL_SECONDS: ClassVar[float] = 1.0
    MS_PER_SECOND: ClassVar[int] = 1000
    BUCKETS_MS: ClassVar[tuple[float, ...]] = (1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000)

    def __init__(self, meter: Meter, interval: float = INTERVAL_SECONDS) -> None:
        self._interval = interval
        self._lag = meter.create_histogram(
            'event_loop.lag',
            unit='ms',
            description='How late the event loop woke a sleeper',
            explicit_bucket_boundaries_advisory=self.BUCKETS_MS,
        )

    async def run(self) -> None:
        while True:
            await self.sample()

    async def sample(self) -> None:
        loop = asyncio.get_running_loop()
        asleep_at = loop.time()
        await asyncio.sleep(self._interval)
        late = loop.time() - asleep_at - self._interval
        self._lag.record(max(late, 0) * self.MS_PER_SECOND)
