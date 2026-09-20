import pytest
from langchain_core.prompts import PromptTemplate
from langsmith.utils import LangSmithError

from bot.infrastructure.llm.langsmith_prompt_registry import (
    LangSmithPromptRegistry,
    PromptRegistryError,
)

_CLIENT_PATH = 'bot.infrastructure.llm.langsmith_prompt_registry.Client'


def _pulled(template: str, commit_hash: str) -> PromptTemplate:
    prompt = PromptTemplate.from_template(template)
    prompt.metadata = {'lc_hub_commit_hash': commit_hash}
    return prompt


class TestSystemPrompt:
    def test_pulls_prompt_by_name_and_tag(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.return_value = _pulled('sys {command_list}', 'c0ffee')
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        prompt = registry.system_prompt()

        client.pull_prompt.assert_called_once_with('resenhazord-agent:prod')
        assert prompt.template == 'sys {command_list}'

    def test_reports_commit_hash_as_version(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.return_value = _pulled('sys {command_list}', 'c0ffee')
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        prompt = registry.system_prompt()

        assert prompt.version == 'c0ffee'

    def test_version_is_empty_when_metadata_absent(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.return_value = PromptTemplate.from_template('sys {command_list}')
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        prompt = registry.system_prompt()

        assert prompt.version == ''

    def test_wraps_pull_failure_in_prompt_registry_error(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.side_effect = LangSmithError('hub down')
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        with pytest.raises(PromptRegistryError, match='hub down'):
            registry.system_prompt()

    def test_rejects_prompt_without_string_template(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.return_value = object()
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        with pytest.raises(PromptRegistryError):
            registry.system_prompt()


class TestConfiguration:
    def test_from_credentials_builds_name_tag_identifier(self, mocker):
        mocker.patch(_CLIENT_PATH)

        registry = LangSmithPromptRegistry.from_credentials('key', 'resenhazord-agent', 'prod')

        assert registry._prompt_identifier == 'resenhazord-agent:prod'

    def test_configure_sets_singleton(self, mocker):
        mocker.patch(_CLIENT_PATH)

        configured = LangSmithPromptRegistry.configure('key', 'resenhazord-agent', 'prod')

        assert LangSmithPromptRegistry.configured() is configured

    def test_configured_is_none_before_configure(self):
        assert LangSmithPromptRegistry.configured() is None
