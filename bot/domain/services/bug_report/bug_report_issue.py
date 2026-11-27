from dataclasses import dataclass
from typing import Any, ClassVar

from bot.data.bug_report import BUG_REPORT_LABELS, EXTERNAL_API_LABEL
from bot.domain.services.bug_report.bug_report_body import BugReportBody
from bot.domain.services.bug_report.telemetry_links import TelemetryLinks


@dataclass(frozen=True)
class BugReportIssue:
    """The GitHub issue a ,bug files from an execution record."""

    title: str
    body: str
    labels: list[str]

    MAX_TITLE_CHARS: ClassVar[int] = 80
    # GitHub refuses a body over 65 536 characters.
    MAX_BODY_CHARS: ClassVar[int] = 60_000
    NO_RUN: ClassVar[str] = BugReportBody.NO_RUN
    _EXTERNAL_OUTCOME: ClassVar[str] = 'external_error'

    @classmethod
    def of(
        cls, record: dict[str, Any], description: str, reply_id: str, links: TelemetryLinks
    ) -> BugReportIssue:
        execution: dict[str, Any] = record['execution'] or {}
        outcome = execution.get('outcome')
        labels = [*BUG_REPORT_LABELS]
        if outcome == cls._EXTERNAL_OUTCOME:
            labels.append(EXTERNAL_API_LABEL)
        body = BugReportBody(record, links).render(description, reply_id)
        return cls(cls._title(execution, description), body[: cls.MAX_BODY_CHARS], labels)

    @classmethod
    def _title(cls, execution: dict[str, Any], description: str) -> str:
        if not execution:
            return f'bug: {description}'[: cls.MAX_TITLE_CHARS]
        summary = description or execution['outcome']
        return f',{execution["command"]}: {summary}'[: cls.MAX_TITLE_CHARS]
