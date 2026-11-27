import pytest

from bot.infrastructure.telemetry_buffer import TelemetryBuffer


@pytest.fixture(autouse=True)
def _drain_leftovers():
    yield
    assert TelemetryBuffer.held() == 0


class TestPerCommandCap:
    def test_keeps_entries_up_to_its_limit(self):
        buffer = TelemetryBuffer(limit=2)

        for index in range(3):
            buffer.append({'index': index})

        assert buffer.drain() == ([{'index': 0}, {'index': 1}], 1)

    def test_drain_reports_nothing_dropped_under_the_limit(self):
        buffer = TelemetryBuffer(limit=2)
        buffer.append({'index': 0})

        assert buffer.drain() == ([{'index': 0}], 0)


class TestGlobalCap:
    def test_buffers_share_one_budget(self, mocker):
        mocker.patch.object(TelemetryBuffer, 'GLOBAL_LIMIT', 3)
        first, second = TelemetryBuffer(limit=2), TelemetryBuffer(limit=2)

        for index in range(2):
            first.append({'index': index})
            second.append({'index': index})

        assert (len(first.drain()[0]), second.drain()) == (2, ([{'index': 0}], 1))

    def test_draining_returns_the_budget(self, mocker):
        mocker.patch.object(TelemetryBuffer, 'GLOBAL_LIMIT', 1)
        first = TelemetryBuffer()
        first.append({'index': 0})
        first.drain()
        second = TelemetryBuffer()

        second.append({'index': 1})

        assert second.drain() == ([{'index': 1}], 0)

    def test_held_counts_entries_across_buffers(self):
        first, second = TelemetryBuffer(), TelemetryBuffer()
        first.append({'index': 0})
        second.append({'index': 1})

        held = TelemetryBuffer.held()
        first.drain()
        second.drain()

        assert held == 2


class TestClosed:
    def test_a_drained_buffer_takes_nothing_more(self):
        buffer = TelemetryBuffer()
        buffer.drain()

        buffer.append({'late': True})

        assert buffer.drain() == ([], 1)

    def test_a_late_entry_holds_no_budget(self):
        buffer = TelemetryBuffer()
        buffer.drain()

        buffer.append({'late': True})

        assert TelemetryBuffer.held() == 0
