from typing import Any, ClassVar

from bot.domain.services.bug_report.markdown import Markdown
from bot.domain.services.bug_report.span_tree import SpanTree
from bot.domain.services.bug_report.telemetry_links import TelemetryLinks


class BugReportBody:
    """The issue body: the report, the command, its failure and its telemetry.

    Every value comes from an execution record already redacted at capture; here it
    is only escaped for markdown.
    """

    NO_RUN: ClassVar[str] = '_No command ran for this reply: it was a rejection or a built-in._'
    FOOTER: ClassVar[str] = (
        '---\nFiled with `,bug`. Chat and user ids are keyed hashes; credentials, query '
        'strings and phone numbers are redacted.'
    )
    _BYTES_PER_MB: ClassVar[int] = 1024 * 1024
    _CLOCK: ClassVar[slice] = slice(11, 23)

    def __init__(self, record: dict[str, Any], links: TelemetryLinks) -> None:
        self._record = record
        self._execution: dict[str, Any] = record['execution'] or {}
        self._links = links

    def render(self, description: str, reply_id: str) -> str:
        sections = [
            self._report(description, reply_id),
            self._command(),
            self._failure(),
            self._telemetry(),
            self.FOOTER,
        ]
        return '\n\n'.join(section for section in sections if section)

    def _report(self, description: str, reply_id: str) -> str:
        reply = self._record['replies'].get(reply_id, '')
        return '\n\n'.join(
            [
                '## Report',
                Markdown.quote(description or '(no description)'),
                f'Marked reply {Markdown.code(reply_id)}:',
                Markdown.quote(reply or '(empty)'),
            ]
        )

    def _command(self) -> str:
        if not self._execution:
            return f'## Command\n\n{self.NO_RUN}'
        record, run = self._record, self._execution
        rows = {
            'Command': Markdown.code(f',{run["command"]}'),
            'Text': Markdown.code(run['text']),
            'Flags': Markdown.code(' '.join(run['flags'])),
            'Options': Markdown.code(run['options']),
            'Args': Markdown.code(run['args']),
            'Platform': f'{record["platform"]}, {record["chat_type"]}',
            'Chat / sender': f'{Markdown.code(record["chat"])} / {Markdown.code(record["sender"])}',
            'Message id': Markdown.code(record['message_id']),
            'Correlation id': Markdown.code(record['correlation_id']),
            'Attempt': record['attempt'],
            'Received': record['received_at'],
            'Started / finished': f'{run["started_at"]} / {run["finished_at"]}',
            'Duration': f'{run["duration_ms"]} ms',
            'Outcome': Markdown.code(run['outcome']),
        }
        table = '\n'.join(f'| {name} | {value} |' for name, value in rows.items())
        return f'## Command\n\n| Field | Value |\n|---|---|\n{table}'

    def _failure(self) -> str:
        failure = self._execution.get('failure')
        if not failure:
            return ''
        parts = [
            '## Failure',
            f'**{Markdown.code(failure["type"])}**: {Markdown.text(failure["message"])}',
        ]
        if frame := failure['frame']:
            arguments = '\n'.join(
                f'| {Markdown.code(name)} | {Markdown.code(value)} |'
                for name, value in frame['arguments'].items()
            )
            parts.append(
                f'Failing frame: {Markdown.code(frame["function"])}, line {frame["line"]}\n\n'
                f'| Argument | Value |\n|---|---|\n{arguments}'
            )
        stack = failure['stack'].replace('```', "'''")
        parts.append(f'<details><summary>Stack</summary>\n\n```text\n{stack}\n```\n\n</details>')
        if sentry := self._links.sentry(self._record['correlation_id']):
            parts.append(f'[Sentry events]({sentry})')
        return '\n\n'.join(parts)

    def _telemetry(self) -> str:
        record = self._record
        parts = ['## Telemetry']
        if trace_id := self._execution.get('trace_id'):
            links = [
                f'[{name}]({url})'
                for name, url in (
                    ('Tempo', self._links.tempo(trace_id)),
                    ('Loki', self._links.loki(trace_id)),
                )
                if url
            ]
            parts.append(' · '.join([f'Trace {Markdown.code(trace_id)}', *links]))
        spans = '\n'.join(SpanTree.rows(record['spans']))
        parts.append(
            f'| Span | Total | Self | Status | Upstream |\n|---|---:|---:|---|---|\n{spans}'
            + self._dropped(record['spans_dropped'], 'spans')
        )
        logs = '\n'.join(self._log_row(line) for line in record['logs'])
        parts.append(
            f'| Time | Level | Event | Fields |\n|---|---|---|---|\n{logs}'
            + self._dropped(record['logs_dropped'], 'log lines')
        )
        host = record['host']
        parts.append(
            f'Host: RSS {round(host["rss_bytes"] / self._BYTES_PER_MB)} MB · '
            f'loop lag {host["loop_lag_ms"]} ms · {host["in_flight"]} in flight'
        )
        return '\n\n'.join(parts)

    @classmethod
    def _log_row(cls, line: dict[str, Any]) -> str:
        fields = ' '.join(f'{key}={value}' for key, value in line['fields'].items())
        clock = str(line['timestamp'] or '')[cls._CLOCK]
        event = Markdown.code(line['event'])
        return f'| {clock} | {line["level"]} | {event} | {Markdown.text(fields)} |'

    @staticmethod
    def _dropped(count: int, what: str) -> str:
        return f'\n\n_{count} more {what} dropped by the capture caps._' if count else ''
