import json
from http import HTTPStatus

import httpx
import pytest
import respx
from langchain_core.prompts import PromptTemplate
from langsmith.utils import LangSmithConflictError

from bot.data.agent_examples import SYSTEM_PROMPT_TEMPLATE
from bot.settings import Settings
from scripts.push_prompt import push_prompt

_CLIENT_PATH = 'scripts.push_prompt.Client'
_REPO = 'https://api.smith.langchain.com/repos/-/resenhazord-agent'
_COMMITS = 'https://api.smith.langchain.com/commits/-/resenhazord-agent'
_NEW_ID = 'ba31a2cd-6643-4b4b-97d3-77279348bef5'
_OLD_ID = '25025548-d1c5-4ae0-862f-861b5e8f93e3'


@pytest.fixture
def settings() -> Settings:
    return Settings(langsmith_api_key='key', langsmith_prompt_name='resenhazord-agent')


@pytest.fixture
def sdk(mocker):
    return mocker.patch(_CLIENT_PATH).return_value


@pytest.fixture
def hub():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__startswith=_COMMITS).mock(
            return_value=httpx.Response(
                HTTPStatus.OK,
                json={
                    'commits': [
                        {'commit_hash': 'ac000235e1f2', 'id': _NEW_ID},
                        {'commit_hash': '1a5bf354cd5c', 'id': _OLD_ID},
                    ]
                },
            )
        )
        yield mock


def tagged(hub, tag: str, status: HTTPStatus = HTTPStatus.OK):
    return hub.patch(f'{_REPO}/tags/{tag}').mock(return_value=httpx.Response(status))


class TestPushPrompt:
    def test_commits_the_template_without_tagging_it(self, settings, sdk, hub):
        tagged(hub, 'dev')

        push_prompt(settings, 'dev')

        sdk.push_prompt.assert_called_once_with(
            'resenhazord-agent', object=PromptTemplate.from_template(SYSTEM_PROMPT_TEMPLATE)
        )

    def test_moves_an_existing_tag_to_the_new_commit(self, settings, sdk, hub):
        moved = tagged(hub, 'dev')

        push_prompt(settings, 'dev')

        assert json.loads(moved.calls.last.request.content) == {'commit_id': _NEW_ID}

    def test_creates_a_tag_the_hub_lacks(self, settings, sdk, hub):
        tagged(hub, 'prod', HTTPStatus.NOT_FOUND)
        created = hub.post(f'{_REPO}/tags').mock(return_value=httpx.Response(HTTPStatus.OK))

        push_prompt(settings, 'prod')

        assert json.loads(created.calls.last.request.content) == {
            'tag_name': 'prod',
            'commit_id': _NEW_ID,
        }

    def test_tags_the_latest_commit_when_the_template_is_unchanged(self, settings, sdk, hub):
        sdk.push_prompt.side_effect = LangSmithConflictError('Nothing to commit')
        moved = tagged(hub, 'dev')

        push_prompt(settings, 'dev')

        assert json.loads(moved.calls.last.request.content) == {'commit_id': _NEW_ID}

    def test_fails_when_the_hub_refuses_the_tag(self, settings, sdk, hub):
        tagged(hub, 'dev', HTTPStatus.INTERNAL_SERVER_ERROR)

        with pytest.raises(httpx.HTTPStatusError):
            push_prompt(settings, 'dev')
