"""Push the in-code system prompt to the LangSmith Prompt Hub as a new version.

Run after editing SYSTEM_PROMPT_TEMPLATE to sync the repo's seed into the hub:

    uv run task prompt:push                 # tags the new commit `dev`
    uv run task prompt:push -- --tag prod   # first-time bootstrap straight to prod

Every push is an immutable commit (the hub's version history), and the tag moves
to it even when it already points elsewhere. Pushing an unchanged template moves
the tag to the latest commit, which is that template. Promotion to the
`prod` alias the bot pulls at runtime is a separate, eval-gated step:
scripts/promote_prompt.py. The bot never pulls `dev`; that alias is what
tests/eval runs against before promotion.
"""

import argparse
import contextlib

from langchain_core.prompts import PromptTemplate
from langsmith import Client
from langsmith.utils import LangSmithConflictError

from bot.data.agent_examples import SYSTEM_PROMPT_TEMPLATE
from bot.settings import Settings
from scripts.prompt_hub import hub_client, latest_commit, move_tag

_MISSING_KEY = 'LANGSMITH_API_KEY is not set; cannot push the prompt'


def push_prompt(settings: Settings, tag: str) -> str:
    name = settings.langsmith_prompt_name
    template = PromptTemplate.from_template(SYSTEM_PROMPT_TEMPLATE)
    # The hub refuses a commit identical to the latest one, which is then the one to tag.
    with contextlib.suppress(LangSmithConflictError):
        Client(api_key=settings.langsmith_api_key).push_prompt(name, object=template)
    with hub_client(settings.langsmith_api_key) as client:
        commit = latest_commit(client, name)
        move_tag(client, name, tag, commit['id'])
    return f'{tag} -> {commit["commit_hash"]}'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default='dev', help='commit alias to attach (default: dev)')
    arguments = parser.parse_args()

    configured = Settings()
    if not configured.langsmith_api_key:
        raise SystemExit(_MISSING_KEY)
    print(push_prompt(configured, arguments.tag))
