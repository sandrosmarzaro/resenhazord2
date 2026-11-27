import re
from typing import ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Command,
    CommandConfig,
    CommandScope,
    ParsedCommand,
    Platform,
)
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.bug_report.bug_report_issue import BugReportIssue
from bot.domain.services.bug_report.telemetry_links import TelemetryLinks
from bot.infrastructure.execution_store import ExecutionStore
from bot.infrastructure.github_issues import GitHubIssues
from bot.infrastructure.issue_filings import IssueFilings
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class BugReportCommand(Command):
    """,bug: files a GitHub issue for the bot reply a dev quotes, from its record.

    WhatsApp and Telegram quote by replying. A Discord slash command can't reply, so
    there the dev passes the message's link or id first, in the same channel.
    """

    NOT_CONFIGURED: ClassVar[str] = 'O ,bug não está configurado: falta o token do GitHub. 🔧'
    USAGE: ClassVar[str] = (
        'Responda a mensagem do bot que deu errado com ,bug [o que houve]. '
        'No Discord: /bug <link da mensagem> [o que houve]. 🐛'
    )
    NOT_FOUND: ClassVar[str] = (
        'Não achei o registro dessa mensagem: guardo só os últimos 3 dias de respostas. 🤷‍♂️'
    )
    IN_PROGRESS: ClassVar[str] = 'Essa issue já está sendo criada. ⏳'
    FILED: ClassVar[str] = '🐛 Issue #{number} criada: {url}'
    ALREADY_FILED: ClassVar[str] = '🐛 Essa issue já foi criada: {url}'
    _DISCORD_MESSAGE: ClassVar[re.Pattern[str]] = re.compile(
        r'(?:https://(?:\w+\.)?discord(?:app)?\.com/channels/[\w@]+/\d+/)?(\d{17,20})(?:\s+|$)'
    )

    def __init__(
        self,
        issues: GitHubIssues | None,
        filings: IssueFilings,
        links: TelemetryLinks,
        store: ExecutionStore | None = None,
    ) -> None:
        super().__init__()
        self._issues = issues
        self._filings = filings
        self._links = links
        self._store = store

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='bug',
            scope=CommandScope.DEV,
            args=ArgType.OPTIONAL,
            args_label='o que houve',
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Abre uma issue no GitHub com o registro da resposta citada.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if self._issues is None:
            return [Reply.to(data).text(self.NOT_CONFIGURED)]
        reply_id, description = self._quoted(data, parsed.rest)
        if reply_id is None:
            return [Reply.to(data).text(self.USAGE)]
        store = self._store or ExecutionStore.instance()
        record = await store.find(str(data.platform), data.jid, reply_id)
        if record is None:
            return [Reply.to(data).text(self.NOT_FOUND)]
        issue = BugReportIssue.of(
            record, TelemetryRedactor.text(description), reply_id, self._links
        )
        return [Reply.to(data).text(await self._file(self._issues, issue, data))]

    def _quoted(self, data: CommandData, rest: str) -> tuple[str | None, str]:
        if data.quoted_message_id:
            return data.quoted_message_id, rest
        match = self._DISCORD_MESSAGE.match(rest)
        if data.platform != Platform.DISCORD or match is None:
            return None, rest
        return match.group(1), rest[match.end() :]

    async def _file(self, issues: GitHubIssues, issue: BugReportIssue, data: CommandData) -> str:
        # One issue per ,bug message, whatever redelivery the broker does (ADR 0001).
        key = f'{data.platform}:{data.jid}:{data.message_id}'
        if existing := await self._filings.claim(key):
            in_progress = existing == IssueFilings.IN_PROGRESS
            return self.IN_PROGRESS if in_progress else self.ALREADY_FILED.format(url=existing)
        try:
            filed = await issues.create(issue.title, issue.body, issue.labels)
        except ExternalServiceError:
            await self._filings.release(key)
            raise
        await self._filings.settle(key, filed.url)
        return self.FILED.format(number=filed.number, url=filed.url)
