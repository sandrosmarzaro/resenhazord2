import time

import anyio
import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from bot.infrastructure.runtime_metrics import LoopLagMonitor, register_process_gauges

BLOCK_SECONDS = 0.05
TICK_SECONDS = 0.01


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def reader():
    return InMemoryMetricReader()


@pytest.fixture
def meter(reader):
    return MeterProvider(metric_readers=[reader]).get_meter('test')


def _points(reader, name: str) -> list:
    data = reader.get_metrics_data()
    return [
        point
        for resource in data.resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
        if metric.name == name
        for point in metric.data.data_points
    ]


class TestProcessGauges:
    def test_reports_the_resident_memory(self, meter, reader):
        register_process_gauges(meter)

        [point] = _points(reader, 'process.memory.rss')

        assert point.value > 0

    def test_reports_the_cpu_time_spent(self, meter, reader):
        register_process_gauges(meter)

        [point] = _points(reader, 'process.cpu.time')

        assert point.value > 0


class TestLoopLag:
    @pytest.mark.anyio
    async def test_a_blocked_loop_shows_as_lag(self, meter, reader):
        monitor = LoopLagMonitor(meter, interval=TICK_SECONDS)

        async with anyio.create_task_group() as tg:
            tg.start_soon(monitor.sample)
            await anyio.lowlevel.checkpoint()
            time.sleep(BLOCK_SECONDS)  # noqa: ASYNC251

        [point] = _points(reader, 'event_loop.lag')
        assert point.sum >= (BLOCK_SECONDS - TICK_SECONDS) * 1000

    @pytest.mark.anyio
    async def test_run_keeps_sampling(self, meter, reader):
        monitor = LoopLagMonitor(meter, interval=TICK_SECONDS)

        with anyio.move_on_after(TICK_SECONDS * 5):
            await monitor.run()

        [point] = _points(reader, 'event_loop.lag')
        assert point.count >= 2
