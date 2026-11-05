import threading
from functools import partial

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from bot.infrastructure.work import Work


@pytest.fixture
def spans(mocker):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    mocker.patch.object(Work, '_TRACER', provider.get_tracer('test'))
    return exporter


def _encode(text: str, *, suffix: str = '') -> tuple[str, int]:
    return f'{text}{suffix}', threading.get_ident()


class TestCpu:
    @pytest.mark.anyio
    async def test_runs_off_the_event_loop_thread(self, spans):
        result, thread = await Work.cpu(_encode, 'png')

        assert result == 'png'
        assert thread != threading.get_ident()

    @pytest.mark.anyio
    async def test_marks_the_span_as_cpu_work(self, spans):
        await Work.cpu(_encode, 'png')

        [span] = spans.get_finished_spans()
        assert span.name == 'cpu _encode'
        assert span.attributes['work.kind'] == 'cpu'

    @pytest.mark.anyio
    async def test_names_a_partial_after_its_function(self, spans):
        await Work.cpu(partial(_encode, 'png', suffix='!'))

        assert spans.get_finished_spans()[0].name == 'cpu _encode'

    @pytest.mark.anyio
    async def test_names_a_callable_object_after_its_type(self, spans):
        class Renderer:
            def __call__(self) -> str:
                return 'png'

        await Work.cpu(Renderer())

        assert spans.get_finished_spans()[0].name.endswith('Renderer')

    @pytest.mark.anyio
    async def test_failure_propagates_without_recording_the_message(self, spans):
        def _fail() -> None:
            message = '/bot123:secret'
            raise ValueError(message)

        with pytest.raises(ValueError, match='secret'):
            await Work.cpu(_fail)

        assert not spans.get_finished_spans()[0].events


class TestDetached:
    def test_marks_the_span_as_fire_and_forget(self, spans):
        with Work.detached('birthday.celebrate'):
            pass

        [span] = spans.get_finished_spans()
        assert span.name == 'birthday.celebrate'
        assert span.attributes['work.kind'] == 'fire_and_forget'

    def test_starts_a_new_trace_linked_to_its_creator(self, spans):
        with Work.detached('outer'), Work.detached('birthday.celebrate'):
            pass

        inner, outer = spans.get_finished_spans()
        assert inner.parent is None
        assert inner.links[0].context.span_id == outer.context.span_id
