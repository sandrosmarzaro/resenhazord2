import json

import httpx
import pytest
from fakeredis.aioredis import FakeRedis

from bot.domain.commands.base import CommandScope, Platform
from bot.domain.commands.bug_report import BugReportCommand
from bot.domain.exceptions import ExternalServiceError
from bot.domain.services.bug_report.telemetry_links import TelemetryLinks
from bot.infrastructure.execution_store import ExecutionStore
from bot.infrastructure.github_issues import GitHubIssues
from bot.infrastructure.issue_filings import IssueFilings
from tests.factories.command_data import GroupCommandDataFactory

ISSUES_URL = 'https://api.github.com/repos/owner/repo/issues'
ISSUE_URL = 'https://github.com/owner/repo/issues/432'
REPLY_ID = '3EB0ABCDEF0123456789AB'
DISCORD_REPLY_ID = '1234567890123456789'
RECORD = {
    'platform': 'whatsapp',
    'chat_type': 'group',
    'chat': 'a1b2c3d4e5',
    'sender': 'f6a7b8c9d0',
    'message_id': 'MSG-1',
    'correlation_id': 'corr-1',
    'attempt': 1,
    'received_at': '2026-11-26T12:00:00+00:00',
    'execution': None,
    'spans': [],
    'spans_dropped': 0,
    'logs': [],
    'logs_dropped': 0,
    'host': {'rss_bytes': 1, 'loop_lag_ms': 0.0, 'in_flight': 1},
    'replies': {REPLY_ID: 'pong'},
}


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.fixture
def store(redis):
    return ExecutionStore(redis)


@pytest.fixture
def command(redis, store):
    return BugReportCommand(
        GitHubIssues('test-token', 'owner/repo'), IssueFilings(redis), TelemetryLinks(), store
    )


@pytest.fixture
def github(respx_mock):
    return respx_mock.post(ISSUES_URL).mock(
        return_value=httpx.Response(201, json={'number': 432, 'html_url': ISSUE_URL})
    )


def _bug(text=',bug a cotação veio errada', **overrides):
    defaults = {'platform': Platform.WHATSAPP, 'quoted_message_id': REPLY_ID}
    return GroupCommandDataFactory.build(text=text, **(defaults | overrides))


async def _recorded(store, data, reply_id=REPLY_ID):
    await store.save(RECORD, str(data.platform), data.jid, [reply_id])


def _text(messages) -> str:
    [message] = messages
    return message.content.text


class TestConfig:
    def test_is_dev_only(self, command):
        assert command.config.scope == CommandScope.DEV

    def test_runs_on_every_platform(self, command):
        assert command.config.platforms == [Platform.ALL]

    @pytest.mark.parametrize(('text', 'expected'), [(',bug', True), (',bug veio errado', True)])
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestFiling:
    @pytest.mark.anyio
    async def test_files_the_issue_and_replies_with_its_link(self, command, store, github):
        data = _bug()
        await _recorded(store, data)

        reply = _text(await command.run(data))

        assert reply == f'🐛 Issue #432 criada: {ISSUE_URL}'

    @pytest.mark.anyio
    async def test_the_issue_carries_the_description(self, command, store, github):
        data = _bug()
        await _recorded(store, data)

        await command.run(data)

        assert '> a cotação veio errada' in json.loads(github.calls.last.request.content)['body']

    @pytest.mark.anyio
    async def test_a_phone_in_the_description_is_hashed(self, command, store, github):
        data = _bug(',bug mandou pro 5511999999999')
        await _recorded(store, data)

        await command.run(data)

        assert '5511999999999' not in github.calls.last.request.content.decode()


class TestRedelivery:
    @pytest.mark.anyio
    async def test_a_redelivered_bug_files_once(self, command, store, github):
        data = _bug()
        await _recorded(store, data)
        await command.run(data)

        reply = _text(await command.run(data))

        assert (github.call_count, reply) == (1, f'🐛 Essa issue já foi criada: {ISSUE_URL}')

    @pytest.mark.anyio
    async def test_a_bug_still_filing_is_not_filed_again(self, command, store, redis, github):
        data = _bug()
        await _recorded(store, data)
        await IssueFilings(redis).claim(f'{data.platform}:{data.jid}:{data.message_id}')

        reply = _text(await command.run(data))

        assert (github.call_count, reply) == (0, BugReportCommand.IN_PROGRESS)

    @pytest.mark.anyio
    async def test_a_failed_filing_can_be_retried(self, command, store, respx_mock):
        data = _bug()
        await _recorded(store, data)
        route = respx_mock.post(ISSUES_URL)
        route.side_effect = [
            httpx.Response(502, json={}),
            httpx.Response(201, json={'number': 432, 'html_url': ISSUE_URL}),
        ]
        with pytest.raises(ExternalServiceError):
            await command.run(data)

        reply = _text(await command.run(data))

        assert reply == f'🐛 Issue #432 criada: {ISSUE_URL}'

    @pytest.mark.anyio
    async def test_without_redis_it_still_files(self, store, github):
        command = BugReportCommand(
            GitHubIssues('t', 'owner/repo'), IssueFilings(None), TelemetryLinks(), store
        )
        data = _bug()
        await _recorded(store, data)

        assert _text(await command.run(data)) == f'🐛 Issue #432 criada: {ISSUE_URL}'


class TestRefusals:
    @pytest.mark.anyio
    async def test_without_a_token_it_says_it_is_not_configured(self, store):
        command = BugReportCommand(None, IssueFilings(None), TelemetryLinks(), store)

        assert _text(await command.run(_bug())) == BugReportCommand.NOT_CONFIGURED

    @pytest.mark.anyio
    async def test_without_a_quoted_message_it_explains_the_usage(self, command):
        data = GroupCommandDataFactory.build(text=',bug', platform=Platform.WHATSAPP)

        assert _text(await command.run(data)) == BugReportCommand.USAGE

    @pytest.mark.anyio
    async def test_a_message_without_a_record_files_nothing(self, command, github):
        reply = _text(await command.run(_bug()))

        assert (reply, github.call_count) == (BugReportCommand.NOT_FOUND, 0)


class TestDiscord:
    @staticmethod
    def _data(text):
        return GroupCommandDataFactory.build(text=text, platform=Platform.DISCORD, jid='42')

    @pytest.mark.anyio
    async def test_finds_the_message_by_its_link(self, command, store, github):
        link = f'https://discord.com/channels/1/42/{DISCORD_REPLY_ID}'
        data = self._data(f',bug {link} veio errado')
        await _recorded(store, data, DISCORD_REPLY_ID)

        await command.run(data)

        body = json.loads(github.calls.last.request.content)['body']
        assert ('> veio errado' in body, link not in body) == (True, True)

    @pytest.mark.anyio
    async def test_finds_the_message_by_its_id(self, command, store, github):
        data = self._data(f',bug {DISCORD_REPLY_ID}')
        await _recorded(store, data, DISCORD_REPLY_ID)

        assert _text(await command.run(data)) == f'🐛 Issue #432 criada: {ISSUE_URL}'

    @pytest.mark.anyio
    async def test_without_a_link_it_explains_the_usage(self, command):
        assert _text(await command.run(self._data(',bug veio errado'))) == BugReportCommand.USAGE
