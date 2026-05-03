"""Tests for LLM tool schema builder."""

import pytest

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandConfig, CommandScope
from bot.domain.commands.score import ScoreCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.llm.tools import (
    build_tools_for_prompt,
    command_to_tool_schema,
    get_command_names,
)


class _ScopedCommand(Command):
    def __init__(self, name: str, scope: CommandScope) -> None:
        super().__init__()
        self._name = name
        self._scope = scope

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name=self._name, scope=self._scope)

    @property
    def menu_description(self) -> str:
        return f'{self._name} command'

    async def execute(self, data: CommandData, parsed: object) -> list[BotMessage]:
        return []


class TestCommandToToolSchema:
    @pytest.mark.anyio
    async def test_score_command_generates_valid_tool_schema(self):
        """Test that score command generates valid tool schema."""
        command = ScoreCommand()
        schema = command_to_tool_schema(command)

        assert schema['type'] == 'function'
        assert 'function' in schema
        assert schema['function']['name'] == 'placar'

    @pytest.mark.anyio
    async def test_tool_schema_has_description(self):
        """Test that tool schema includes description."""
        command = ScoreCommand()
        schema = command_to_tool_schema(command)

        assert 'description' in schema['function']
        assert len(schema['function']['description']) > 0

    @pytest.mark.anyio
    async def test_tool_schema_has_flags_as_boolean(self):
        """Test that flags are mapped as boolean properties."""
        command = ScoreCommand()
        schema = command_to_tool_schema(command)

        properties = schema['function']['parameters']['properties']
        assert 'past' in properties
        assert properties['past']['type'] == 'boolean'


class TestBuildToolsForPrompt:
    @pytest.mark.anyio
    async def test_build_tools_returns_list(self):
        """Test that build_tools returns a list."""
        reg = CommandRegistry()
        tools = build_tools_for_prompt(reg)

        assert isinstance(tools, list)

    @pytest.mark.anyio
    async def test_get_command_names_from_registry(self):
        """Test that command names are retrieved."""
        reg = CommandRegistry()
        names = get_command_names(reg)

        assert isinstance(names, list)

    @pytest.mark.anyio
    async def test_tool_schema_structure(self):
        """Test the complete tool schema structure."""
        command = ScoreCommand()
        schema = command_to_tool_schema(command)

        assert schema['type'] == 'function'
        assert schema['function']['name'] == 'placar'
        assert 'past' in schema['function']['parameters']['properties']
        assert 'now' in schema['function']['parameters']['properties']
        assert 'next' in schema['function']['parameters']['properties']


class TestScopeFilter:
    @pytest.fixture
    def registry(self) -> CommandRegistry:
        registry = CommandRegistry()
        registry.register(_ScopedCommand('public_one', CommandScope.PUBLIC))
        registry.register(_ScopedCommand('internal_one', CommandScope.INTERNAL))
        registry.register(_ScopedCommand('dev_one', CommandScope.DEV))
        registry.register(_ScopedCommand('admin_one', CommandScope.ADMIN))
        registry.register(_ScopedCommand('nsfw_one', CommandScope.NSFW))
        registry.register(_ScopedCommand('disabled_one', CommandScope.DISABLED))
        return registry

    @pytest.mark.anyio
    async def test_public_default_excludes_nsfw_and_disabled(self, registry):
        names = {tool['function']['name'] for tool in build_tools_for_prompt(registry)}

        assert names == {'public_one', 'internal_one', 'dev_one', 'admin_one'}

    @pytest.mark.anyio
    async def test_dev_scope_filters_lower_priority_commands(self, registry):
        names = {
            tool['function']['name']
            for tool in build_tools_for_prompt(registry, include_scope=CommandScope.DEV)
        }

        assert names == {'dev_one', 'admin_one'}

    @pytest.mark.anyio
    async def test_admin_scope_keeps_only_admin(self, registry):
        names = {
            tool['function']['name']
            for tool in build_tools_for_prompt(registry, include_scope=CommandScope.ADMIN)
        }

        assert names == {'admin_one'}

    @pytest.mark.anyio
    async def test_explicit_exclude_overrides_default(self, registry):
        names = {
            tool['function']['name']
            for tool in build_tools_for_prompt(
                registry, exclude_scopes=frozenset({CommandScope.INTERNAL})
            )
        }

        assert 'internal_one' not in names
        assert 'nsfw_one' in names
