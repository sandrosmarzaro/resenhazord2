import pytest
from langchain_core.prompts import PromptTemplate
from langsmith.utils import LangSmithError

from bot.infrastructure.llm.langsmith_prompt_registry import (
    LangSmithPromptRegistry,
    PromptRegistryError,
)

_CLIENT_PATH = 'bot.infrastructure.llm.langsmith_prompt_registry.Client'


class TestSystemPromptTemplate:
    def test_pulls_prompt_by_name_and_tag(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.return_value = PromptTemplate.from_template('sys {command_list}')
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        template = registry.system_prompt_template()

        client.pull_prompt.assert_called_once_with('resenhazord-agent:prod')
        assert template == 'sys {command_list}'

    def test_wraps_pull_failure_in_prompt_registry_error(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.side_effect = LangSmithError('hub down')
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        with pytest.raises(PromptRegistryError, match='hub down'):
            registry.system_prompt_template()

    def test_rejects_prompt_without_string_template(self, mocker):
        client = mocker.Mock()
        client.pull_prompt.return_value = object()
        registry = LangSmithPromptRegistry(client, 'resenhazord-agent:prod')

        with pytest.raises(PromptRegistryError):
            registry.system_prompt_template()


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
