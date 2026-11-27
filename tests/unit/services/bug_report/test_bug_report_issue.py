import copy

import pytest

from bot.domain.services.bug_report.bug_report_issue import BugReportIssue
from bot.domain.services.bug_report.telemetry_links import TelemetryLinks

TRACE = '0af7651916cd43dd8448eb211c80319c'
MS = 1_000_000

RECORD = {
    'platform': 'whatsapp',
    'chat_type': 'group',
    'chat': 'a1b2c3d4e5',
    'sender': 'f6a7b8c9d0',
    'message_id': 'MSG-1',
    'correlation_id': 'corr-1',
    'attempt': 1,
    'received_at': '2026-11-26T12:00:00.000+00:00',
    'execution': {
        'command': 'moeda',
        'text': ',moeda iene',
        'flags': ['dm'],
        'options': {},
        'args': 'iene',
        'started_at': '2026-11-26T12:00:00.010+00:00',
        'finished_at': '2026-11-26T12:00:00.822+00:00',
        'duration_ms': 812,
        'outcome': 'success',
        'trace_id': TRACE,
        'failure': None,
    },
    'spans': [
        {
            'name': 'command.run',
            'span_id': 'a',
            'parent_id': None,
            'start_ns': 0,
            'end_ns': 812 * MS,
            'status': 'UNSET',
            'attributes': {},
        }
    ],
    'spans_dropped': 0,
    'logs': [
        {
            'timestamp': '2026-11-26T12:00:00.820000Z',
            'level': 'info',
            'event': 'command_completed',
            'fields': {'command': 'moeda', 'outcome': 'success'},
        }
    ],
    'logs_dropped': 0,
    'host': {'rss_bytes': 312 * 1024 * 1024, 'loop_lag_ms': 4.0, 'in_flight': 1},
    'replies': {'3EB0A': '¥1 = R$0,03'},
}

FAILURE = {
    'type': 'ExternalServiceError',
    'message': 'Sem cotação agora',
    'stack': 'ExternalServiceError\n  bot/domain/commands/currency.py:42 in execute',
    'frame': {'function': 'CurrencyCommand.execute', 'line': 42, 'arguments': {'page': '2'}},
}


def _record(**changes) -> dict:
    record = copy.deepcopy(RECORD)
    for key, value in changes.items():
        record[key] = value
    return record


def _failed(outcome='external_error') -> dict:
    record = _record()
    record['execution'] |= {'outcome': outcome, 'failure': FAILURE}
    return record


def _issue(record=None, description='a cotação veio errada', links=None) -> BugReportIssue:
    return BugReportIssue.of(record or _record(), description, '3EB0A', links or TelemetryLinks())


class TestTitle:
    def test_names_the_command_and_the_description(self):
        assert _issue().title == ',moeda: a cotação veio errada'

    def test_without_a_description_names_the_outcome(self):
        assert _issue(_failed(), description='').title == ',moeda: external_error'

    def test_a_reply_without_a_run_is_still_titled(self):
        assert _issue(_record(execution=None)).title == 'bug: a cotação veio errada'

    def test_is_capped(self):
        assert len(_issue(description='x' * 500).title) == BugReportIssue.MAX_TITLE_CHARS


class TestLabels:
    def test_a_report_is_a_bug_from_the_bot(self):
        assert _issue().labels == ['bug', 'from-bot']

    def test_an_external_failure_adds_the_api_label(self):
        assert _issue(_failed()).labels == ['bug', 'from-bot', 'external-api']


class TestReport:
    def test_quotes_the_description(self):
        assert '> a cotação veio errada' in _issue().body

    def test_a_mention_in_the_description_pings_nobody(self):
        assert '@sandro' not in _issue(description='olha isso @sandro').body

    def test_quotes_the_marked_reply(self):
        assert '> ¥1 = R$0,03' in _issue().body


class TestCommand:
    @pytest.mark.parametrize(
        'expected',
        [
            '| Text | `,moeda iene` |',
            '| Flags | `dm` |',
            '| Args | `iene` |',
            '| Platform | whatsapp, group |',
            '| Chat / sender | `a1b2c3d4e5` / `f6a7b8c9d0` |',
            '| Correlation id | `corr-1` |',
            '| Attempt | 1 |',
            '| Duration | 812 ms |',
            '| Outcome | `success` |',
        ],
    )
    def test_shows_the_field(self, expected):
        assert expected in _issue().body

    def test_a_reply_without_a_run_says_so(self):
        assert BugReportIssue.NO_RUN in _issue(_record(execution=None)).body


class TestFailure:
    def test_a_success_has_no_failure_section(self):
        assert '## Failure' not in _issue().body

    def test_names_the_error(self):
        assert '**`ExternalServiceError`**: Sem cotação agora' in _issue(_failed()).body

    def test_shows_the_failing_frame_and_its_arguments(self):
        body = _issue(_failed()).body

        assert ('`CurrencyCommand.execute`, line 42' in body, '| `page` | `2` |' in body) == (
            True,
            True,
        )

    def test_folds_the_stack(self):
        assert 'currency.py:42 in execute' in _issue(_failed()).body

    def test_links_the_sentry_events(self):
        body = _issue(_failed(), links=TelemetryLinks(sentry_org='acme')).body

        assert '[Sentry events](https://acme.sentry.io/' in body

    def test_a_frame_outside_the_bot_is_left_out(self):
        record = _failed()
        record['execution']['failure'] = FAILURE | {'frame': None}

        assert 'Failing frame' not in _issue(record).body


class TestTelemetry:
    def test_names_the_trace(self):
        assert f'Trace `{TRACE}`' in _issue().body

    def test_links_tempo_and_loki(self):
        body = _issue(links=TelemetryLinks(grafana_url='https://stack.grafana.net')).body

        assert ('[Tempo](https://stack' in body, '[Loki](https://stack' in body) == (True, True)

    def test_without_a_trace_there_is_no_trace_line(self):
        record = _record()
        record['execution']['trace_id'] = None

        assert 'Trace `' not in _issue(record).body

    def test_lists_the_spans(self):
        assert '| `command.run` | 812 ms | 812 ms | UNSET |  |' in _issue().body

    def test_lists_the_log_lines(self):
        assert '| 12:00:00.820 | info | `command_completed` |' in _issue().body

    def test_counts_what_the_caps_dropped(self):
        body = _issue(_record(spans_dropped=3, logs_dropped=2)).body

        assert ('3 more spans dropped' in body, '2 more log lines dropped' in body) == (True, True)

    def test_describes_the_host(self):
        assert 'RSS 312 MB · loop lag 4.0 ms · 1 in flight' in _issue().body


class TestSize:
    def test_the_body_fits_a_github_issue(self):
        logs = [RECORD['logs'][0] | {'event': 'x' * 300}] * 2000

        assert len(_issue(_record(logs=logs)).body) <= BugReportIssue.MAX_BODY_CHARS
