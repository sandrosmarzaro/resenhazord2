import json
from http import HTTPStatus

import httpx
import pytest
import respx

from bot.settings import Settings
from scripts.promote_prompt import promote_prompt

_REPO = 'https://api.smith.langchain.com/repos/-/resenhazord-agent'
_COMMITS = 'https://api.smith.langchain.com/commits/-/resenhazord-agent'
_DEV_ID = '25025548-d1c5-4ae0-862f-861b5e8f93e3'
_OLD_ID = '20c527fc-51bc-4794-89a5-5ab6c6416f69'


@pytest.fixture
def settings() -> Settings:
    return Settings(langsmith_api_key='key', langsmith_prompt_name='resenhazord-agent')


@pytest.fixture
def hub():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f'{_REPO}/tags').mock(
            return_value=httpx.Response(
                200,
                json=[
                    {'tag_name': 'dev', 'commit_hash': '1a5bf354', 'commit_id': _DEV_ID},
                    {'tag_name': 'prod', 'commit_hash': '6630920a', 'commit_id': _OLD_ID},
                ],
            )
        )
        mock.get(url__startswith=_COMMITS).mock(
            return_value=httpx.Response(
                200,
                json={
                    'commits': [
                        {'commit_hash': '1a5bf354cd5c', 'id': _DEV_ID},
                        {'commit_hash': '6630920a9666', 'id': _OLD_ID},
                    ]
                },
            )
        )
        mock.patch(f'{_REPO}/tags/prod', name='prod').mock(
            return_value=httpx.Response(200, json={'tag_name': 'prod', 'commit_id': _DEV_ID})
        )
        yield mock


class TestPromotePrompt:
    def test_moves_prod_to_the_commit_behind_an_alias(self, settings, hub):
        promote_prompt(settings, 'dev')

        assert json.loads(hub['prod'].calls.last.request.content) == {'commit_id': _DEV_ID}

    def test_moves_prod_to_a_commit_hash_prefix(self, settings, hub):
        promote_prompt(settings, '6630920a')

        assert json.loads(hub['prod'].calls.last.request.content) == {'commit_id': _OLD_ID}

    def test_sends_the_api_key(self, settings, hub):
        promote_prompt(settings, 'dev')

        assert hub['prod'].calls.last.request.headers['x-api-key'] == 'key'

    def test_rejects_an_unknown_source(self, settings, hub):
        with pytest.raises(SystemExit):
            promote_prompt(settings, 'nope')

    def test_creates_prod_when_the_hub_has_none(self, settings, hub):
        hub['prod'].return_value = httpx.Response(HTTPStatus.NOT_FOUND)
        created = hub.post(f'{_REPO}/tags').mock(return_value=httpx.Response(HTTPStatus.OK))

        promote_prompt(settings, 'dev')

        assert json.loads(created.calls.last.request.content) == {
            'tag_name': 'prod',
            'commit_id': _DEV_ID,
        }
