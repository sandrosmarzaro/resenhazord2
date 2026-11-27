from bot.domain.services.bug_report.span_tree import SpanTree

MS = 1_000_000


def _span(span_id, parent_id, start_ms, end_ms, name='x', **attributes):
    return {
        'name': name,
        'span_id': span_id,
        'parent_id': parent_id,
        'start_ns': start_ms * MS,
        'end_ns': end_ms * MS,
        'status': 'UNSET',
        'attributes': attributes,
    }


class TestRows:
    def test_nests_a_child_under_its_parent(self):
        spans = [_span('b', 'a', 10, 60, 'GET'), _span('a', None, 0, 100, 'command.run')]

        rows = SpanTree.rows(spans)

        assert (rows[0].startswith('| `command.run`'), rows[1].startswith('| ↳ `GET`')) == (
            True,
            True,
        )

    def test_shows_total_and_self_time(self):
        spans = [_span('a', None, 0, 100, 'command.run'), _span('b', 'a', 10, 60, 'GET')]

        assert '| 100 ms | 50 ms |' in SpanTree.rows(spans)[0]

    def test_shows_the_upstream_call(self):
        attributes = {
            'http.method': 'GET',
            'server.address': 'open.er-api.com',
            'http.status_code': '200',
        }

        [row] = SpanTree.rows([_span('a', None, 0, 5, 'GET', **attributes)])

        assert row.endswith('| GET open.er-api.com 200 |')

    def test_a_span_whose_parent_was_not_captured_is_a_root(self):
        [row] = SpanTree.rows([_span('b', 'gateway', 0, 5, 'command.handle')])

        assert row.startswith('| `command.handle`')

    def test_orders_siblings_by_start(self):
        spans = [
            _span('a', None, 0, 100, 'command.run'),
            _span('c', 'a', 50, 60, 'second'),
            _span('b', 'a', 10, 20, 'first'),
        ]

        rows = SpanTree.rows(spans)

        assert ('`first`' in rows[1], '`second`' in rows[2]) == (True, True)
