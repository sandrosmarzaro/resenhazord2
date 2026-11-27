import json

import httpx
import pytest

from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.github_issues import FiledIssue, GitHubIssues

ISSUES_URL = 'https://api.github.com/repos/owner/repo/issues'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def issues():
    return GitHubIssues('test-token', 'owner/repo')


class TestCreate:
    @pytest.mark.anyio
    async def test_returns_the_filed_issue(self, issues, respx_mock):
        respx_mock.post(ISSUES_URL).mock(
            return_value=httpx.Response(
                201, json={'number': 432, 'html_url': 'https://github.com/owner/repo/issues/432'}
            )
        )

        filed = await issues.create('título', 'corpo', ['bug'])

        assert filed == FiledIssue(432, 'https://github.com/owner/repo/issues/432')

    @pytest.mark.anyio
    async def test_sends_the_title_body_and_labels(self, issues, respx_mock):
        route = respx_mock.post(ISSUES_URL).mock(
            return_value=httpx.Response(201, json={'number': 1, 'html_url': 'u'})
        )

        await issues.create('título', 'corpo', ['bug', 'from-bot'])

        assert json.loads(route.calls.last.request.content) == {
            'title': 'título',
            'body': 'corpo',
            'labels': ['bug', 'from-bot'],
        }

    @pytest.mark.anyio
    async def test_authenticates_with_the_token(self, issues, respx_mock):
        route = respx_mock.post(ISSUES_URL).mock(
            return_value=httpx.Response(201, json={'number': 1, 'html_url': 'u'})
        )

        await issues.create('t', 'b', [])

        assert route.calls.last.request.headers['Authorization'] == 'Bearer test-token'


class TestFailures:
    @pytest.mark.anyio
    async def test_a_refusal_is_an_external_error(self, issues, respx_mock):
        respx_mock.post(ISSUES_URL).mock(return_value=httpx.Response(403, json={}))

        with pytest.raises(ExternalServiceError):
            await issues.create('t', 'b', [])

    @pytest.mark.anyio
    async def test_an_unreachable_api_is_an_external_error(self, issues, respx_mock):
        respx_mock.post(ISSUES_URL).mock(side_effect=httpx.ConnectError('down'))

        with pytest.raises(ExternalServiceError):
            await issues.create('t', 'b', [])
