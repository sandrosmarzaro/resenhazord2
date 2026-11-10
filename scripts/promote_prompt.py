"""Promote a hub commit to the `prod` alias the bot pulls, after eval passes.

    uv run task prompt:promote                    # promote whatever is on `dev`
    uv run task prompt:promote -- --source <hash> # promote a specific commit

Homologation gate: run this only on a commit the prompt-eval workflow has passed
(see .github/workflows/prompt-eval.yml). It moves the `prod` tag to the source
commit; the bot's next pull (SDK cache TTL 300s) serves it with no re-deploy.
Rollback is the same call pointed at an older green commit.

The tag moves through scripts/prompt_hub.py, which also creates `prod` on a hub
that has none.
"""

import argparse

import httpx

from bot.settings import Settings
from scripts.prompt_hub import hub_client, move_tag

_MISSING_KEY = 'LANGSMITH_API_KEY is not set; cannot promote the prompt'
_PROD_TAG = 'prod'
_COMMITS_PAGE = 100


def promote_prompt(settings: Settings, source: str) -> str:
    name = settings.langsmith_prompt_name
    with hub_client(settings.langsmith_api_key) as client:
        commit_id = _commit_id(client, name, source)
        move_tag(client, name, _PROD_TAG, commit_id)
    return f'{_PROD_TAG} -> {source} ({commit_id})'


def _commit_id(client: httpx.Client, name: str, source: str) -> str:
    tags = client.get(f'/repos/-/{name}/tags').raise_for_status().json()
    tagged = [tag['commit_id'] for tag in tags if tag['tag_name'] == source]
    if tagged:
        return tagged[0]
    commits = client.get(f'/commits/-/{name}', params={'limit': _COMMITS_PAGE})
    matches = [
        commit['id']
        for commit in commits.raise_for_status().json()['commits']
        if commit['commit_hash'].startswith(source)
    ]
    if len(matches) != 1:
        message = f'{source!r} names no single commit or tag of {name}'
        raise SystemExit(message)
    return matches[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='dev', help='commit hash or alias to promote')
    arguments = parser.parse_args()

    configured = Settings()
    if not configured.langsmith_api_key:
        raise SystemExit(_MISSING_KEY)
    print(promote_prompt(configured, arguments.source))
