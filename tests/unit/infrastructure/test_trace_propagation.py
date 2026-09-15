from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from bot.infrastructure.trace_propagation import extract_trace_context, inject_trace_context


class TestPropagation:
    def test_inject_writes_traceparent_under_active_span(self):
        tracer = TracerProvider().get_tracer('test')
        carrier: dict = {}

        with tracer.start_as_current_span('publish'):
            inject_trace_context(carrier)

        assert 'traceparent' in carrier

    def test_extract_recovers_the_injected_trace_id(self):
        tracer = TracerProvider().get_tracer('test')
        carrier: dict = {}

        with tracer.start_as_current_span('publish') as span:
            inject_trace_context(carrier)
            sent_trace_id = span.get_span_context().trace_id

        extracted = extract_trace_context(carrier)
        recovered = trace.get_current_span(extracted).get_span_context().trace_id

        assert recovered == sent_trace_id

    def test_inject_without_active_span_writes_nothing(self):
        carrier: dict = {}

        inject_trace_context(carrier)

        assert carrier == {}

    def test_extract_from_empty_carrier_is_a_noop_context(self):
        extracted = extract_trace_context({})

        assert not trace.get_current_span(extracted).get_span_context().is_valid

    def test_child_span_links_across_the_envelope(self):
        # Simulates the edge->core hop: one process injects into the envelope, the
        # other extracts and continues, landing both spans in one trace.
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = provider.get_tracer('test')

        envelope: dict = {}
        with tracer.start_as_current_span('gateway.publish') as parent:
            inject_trace_context(envelope)
            parent_context = parent.get_span_context()

        continued = extract_trace_context(envelope)
        with tracer.start_as_current_span('command.handle', context=continued):
            pass

        child = next(s for s in exporter.get_finished_spans() if s.name == 'command.handle')
        assert child.context.trace_id == parent_context.trace_id
        assert child.parent.span_id == parent_context.span_id
