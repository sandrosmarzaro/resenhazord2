"""LangSmith Prompt Hub REST calls shared by the prompt scripts.

The SDK only creates tags, and the hub answers 409 once a tag exists, so an alias
moves through PATCH and is created only when the hub has none yet.
"""

from http import HTTPStatus

import httpx

_API_URL = 'https://api.smith.langchain.com'
_TIMEOUT_SECONDS = 30.0


def hub_client(api_key: str) -> httpx.Client:
    return httpx.Client(base_url=_API_URL, headers={'x-api-key': api_key}, timeout=_TIMEOUT_SECONDS)


def latest_commit(client: httpx.Client, name: str) -> dict[str, str]:
    commits = client.get(f'/commits/-/{name}', params={'limit': 1}).raise_for_status()
    return commits.json()['commits'][0]


def move_tag(client: httpx.Client, name: str, tag: str, commit_id: str) -> None:
    response = client.patch(f'/repos/-/{name}/tags/{tag}', json={'commit_id': commit_id})
    if response.status_code == HTTPStatus.NOT_FOUND:
        response = client.post(
            f'/repos/-/{name}/tags', json={'tag_name': tag, 'commit_id': commit_id}
        )
    response.raise_for_status()
