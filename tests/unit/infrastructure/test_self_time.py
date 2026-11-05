import pytest
from opentelemetry import trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider

from bot.infrastructure.self_time import SelfTimeProcessor

MS = 1_000_000


@pytest.fixture
def reader():
    return InMemoryMetricReader()


@pytest.fixture
def tracer(reader):
    meter = MeterProvider(metric_readers=[reader]).get_meter('test')
    provider = TracerProvider()
    provider.add_span_processor(SelfTimeProcessor(meter))
    return provider.get_tracer('test')


def _self_times(reader) -> dict[tuple[str, str], float]:
    data = reader.get_metrics_data()
    points = [
        point
        for resource in data.resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
        if metric.name == 'span.self_time'
        for point in metric.data.data_points
    ]
    return {
        (point.attributes['span.name'], point.attributes['work.kind']): point.sum
        for point in points
    }


def _child(tracer, parent, name, start, end, **attributes):
    context = trace.set_span_in_context(parent)
    span = tracer.start_span(name, context=context, start_time=start * MS, attributes=attributes)
    span.end(end_time=end * MS)


class TestSelfTime:
    def test_leaf_span_self_time_is_its_duration(self, tracer, reader):
        tracer.start_span('GET', start_time=0).end(end_time=300 * MS)

        assert _self_times(reader)[('GET', 'io')] == 300

    def test_awaited_child_is_subtracted_from_the_parent(self, tracer, reader):
        parent = tracer.start_span('command.run', start_time=0)
        _child(tracer, parent, 'GET', 100, 700)
        parent.end(end_time=800 * MS)

        assert _self_times(reader)[('command.run', 'io')] == 200

    def test_concurrent_children_subtract_their_union_not_their_sum(self, tracer, reader):
        parent = tracer.start_span('command.run', start_time=0)
        _child(tracer, parent, 'GET', 100, 600)
        _child(tracer, parent, 'GET', 100, 600)
        _child(tracer, parent, 'GET', 500, 700)
        parent.end(end_time=1000 * MS)

        assert _self_times(reader)[('command.run', 'io')] == 400

    def test_child_time_outside_the_parent_window_is_not_subtracted(self, tracer, reader):
        parent = tracer.start_span('command.run', start_time=100 * MS)
        _child(tracer, parent, 'GET', 0, 300)
        parent.end(end_time=500 * MS)

        assert _self_times(reader)[('command.run', 'io')] == 200

    def test_fire_and_forget_child_is_not_subtracted(self, tracer, reader):
        parent = tracer.start_span('command.run', start_time=0)
        _child(tracer, parent, 'typing', 0, 900, **{'work.kind': 'fire_and_forget'})
        parent.end(end_time=1000 * MS)

        assert _self_times(reader)[('command.run', 'io')] == 1000

    def test_carries_the_declared_work_kind(self, tracer, reader):
        span = tracer.start_span('cpu encode', start_time=0, attributes={'work.kind': 'cpu'})
        span.end(end_time=50 * MS)

        assert _self_times(reader)[('cpu encode', 'cpu')] == 50

    def test_child_ending_after_its_parent_leaves_the_parent_self_time_alone(self, tracer, reader):
        parent = tracer.start_span('command.run', start_time=0)
        parent.end(end_time=100 * MS)
        _child(tracer, parent, 'GET', 50, 400)

        assert _self_times(reader)[('command.run', 'io')] == 100
