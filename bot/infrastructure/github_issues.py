from dataclasses import dataclass
from http import HTTPStatus
from typing import ClassVar

import httpx
import structlog

from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


@dataclass(frozen=True)
class FiledIssue:
    number: int
    url: str


class GitHubIssues:
    """Opens issues on the repo through the REST API, with a fine-grained token that
    may only write issues there."""

    API_URL: ClassVar[str] = 'https://api.github.com'
    API_VERSION: ClassVar[str] = '2022-11-28'
    FAILED_MESSAGE: ClassVar[str] = 'Não consegui abrir a issue no GitHub agora, tenta de novo! 🐛'
    _UPSTREAM: ClassVar[str] = 'github'

    def __init__(self, token: str, repository: str) -> None:
        self._url = f'{self.API_URL}/repos/{repository}/issues'
        self._headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': self.API_VERSION,
        }

    async def create(self, title: str, body: str, labels: list[str]) -> FiledIssue:
        try:
            response = await HttpClient.post(
                self._url,
                headers=self._headers,
                json={'title': title, 'body': body, 'labels': labels},
            )
        except httpx.HTTPError as error:
            logger.warning(
                'upstream_failed', upstream=self._UPSTREAM, error_type=type(error).__name__
            )
            raise ExternalServiceError(self.FAILED_MESSAGE) from error
        if response.status_code != HTTPStatus.CREATED:
            logger.warning('upstream_failed', upstream=self._UPSTREAM, status=response.status_code)
            raise ExternalServiceError(self.FAILED_MESSAGE)
        issue = response.json()
        return FiledIssue(issue['number'], issue['html_url'])
