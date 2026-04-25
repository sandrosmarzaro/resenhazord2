"""Tests for LLM tool schema builder."""

import pytest

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.score import ScoreCommand
from bot.infrastructure.llm.tools import (
    build_tools_for_prompt,
    command_to_tool_schema,
    get_command_names,
)


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
