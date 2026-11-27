from collections import defaultdict
from typing import Any, ClassVar

from bot.domain.services.bug_report.markdown import Markdown
from bot.infrastructure.self_time import SelfTimeProcessor


class SpanTree:
    """A command's captured spans as markdown table rows, children under parents.

    Self time is the span's duration minus the union of its children's, the same
    measure span.self_time records, so the slow call is the one with the large self
    time. A span whose parent wasn't captured (the gateway's) is a root.
    """

    NS_PER_MS: ClassVar[int] = 1_000_000
    _INDENT: ClassVar[str] = '↳ '
    _UPSTREAM_ATTRIBUTES: ClassVar[tuple[str, ...]] = (
        'http.method',
        'server.address',
        'http.status_code',
    )

    @classmethod
    def rows(cls, spans: list[dict[str, Any]]) -> list[str]:
        ids = {span['span_id'] for span in spans}
        children: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        for span in sorted(spans, key=lambda span: span['start_ns']):
            parent = span['parent_id'] if span['parent_id'] in ids else None
            children[parent].append(span)
        rows: list[str] = []
        cls._walk(children, None, 0, rows)
        return rows

    @classmethod
    def _walk(
        cls,
        children: dict[str | None, list[dict[str, Any]]],
        parent: str | None,
        depth: int,
        rows: list[str],
    ) -> None:
        for span in children.get(parent, []):
            rows.append(cls._row(span, children.get(span['span_id'], []), depth))
            cls._walk(children, span['span_id'], depth + 1, rows)

    @classmethod
    def _row(cls, span: dict[str, Any], kids: list[dict[str, Any]], depth: int) -> str:
        start, end = span['start_ns'], span['end_ns']
        busy = SelfTimeProcessor.busy_time(
            [(kid['start_ns'], kid['end_ns']) for kid in kids], start
        )
        attributes = span['attributes']
        upstream = ' '.join(
            str(attributes[key]) for key in cls._UPSTREAM_ATTRIBUTES if key in attributes
        )
        name = f'{cls._INDENT * depth}{Markdown.code(span["name"])}'
        total_ms = round((end - start) / cls.NS_PER_MS)
        self_ms = round((end - start - busy) / cls.NS_PER_MS)
        cells = (name, f'{total_ms} ms', f'{self_ms} ms', span['status'], Markdown.text(upstream))
        return f'| {" | ".join(cells)} |'
