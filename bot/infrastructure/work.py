"""Spans that say what kind of work a call is, for span.self_time.

An unmarked span is awaited I/O. `cpu` runs a blocking function on a worker
thread under a `work.kind=cpu` span, so encoding and rendering time shows up
apart from the network. `detached` is for work nobody awaits (scheduled jobs,
background loops): it starts its own trace, linked to whatever spawned it, so
its time never lands on a request's latency or self time.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import ClassVar

import anyio
from opentelemetry import trace
from opentelemetry.trace import Link, Tracer


class Work:
    _TRACER: ClassVar[Tracer] = trace.get_tracer(__name__)
    # The automatic exception record would copy the message onto the span, and a
    # message can carry a URL with secrets in it. The command span classifies the error.
    _QUIET: ClassVar[dict[str, bool]] = {
        'record_exception': False,
        'set_status_on_exception': False,
    }

    @classmethod
    async def cpu[T](cls, func: Callable[..., T], *args: object) -> T:
        target = getattr(func, 'func', func)
        name = f'cpu {target.__qualname__}'
        # No automatic exception record: the message can carry a URL with secrets in
        # it, and the command span already classifies the failure.
        with cls._TRACER.start_as_current_span(
            name,
            attributes={'work.kind': 'cpu'},
            record_exception=False,
            set_status_on_exception=False,
        ):
            return await anyio.to_thread.run_sync(func, *args)

    @classmethod
    @contextmanager
    def detached(cls, name: str) -> Iterator[None]:
        creator = trace.get_current_span().get_span_context()
        links = [Link(creator)] if creator.is_valid else []
        with cls._TRACER.start_as_current_span(
            name,
            context=trace.set_span_in_context(trace.INVALID_SPAN),
            links=links,
            attributes={'work.kind': 'fire_and_forget'},
            record_exception=False,
            set_status_on_exception=False,
        ):
            yield
