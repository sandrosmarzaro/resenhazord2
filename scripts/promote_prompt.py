"""Promote a hub commit to the `prod` alias the bot pulls, after eval passes.

    uv run task prompt:promote                    # promote whatever is on `dev`
    uv run task prompt:promote -- --source <hash> # promote a specific commit

Homologation gate: run this only on a commit the prompt-eval workflow has passed
(see .github/workflows/prompt-eval.yml). It pulls the source commit and re-tags
its content as `prod`; the bot's next pull (SDK cache TTL 300s) serves it with no
re-deploy. Rollback is the same call pointed at an older green commit.
"""

import argparse

from langsmith import Client

from bot.settings import Settings

_MISSING_KEY = 'LANGSMITH_API_KEY is not set; cannot promote the prompt'
_PROD_TAG = 'prod'


def promote_prompt(settings: Settings, source: str) -> str:
    client = Client(api_key=settings.langsmith_api_key)
    identifier = f'{settings.langsmith_prompt_name}:{source}'
    committed = client.pull_prompt(identifier)
    return client.push_prompt(
        settings.langsmith_prompt_name, object=committed, commit_tags=[_PROD_TAG]
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='dev', help='commit hash or alias to promote')
    arguments = parser.parse_args()

    configured = Settings()
    if not configured.langsmith_api_key:
        raise SystemExit(_MISSING_KEY)
    print(promote_prompt(configured, arguments.source))
