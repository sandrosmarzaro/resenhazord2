"""Tests for Agent Executor."""

import pytest

from bot.application.agent_executor import AgentExecutor
from bot.domain.models.command_data import CommandData


class TestAgentExecutor:
    @pytest.mark.anyio
    async def test_executor_initializes(self):
        """Test that executor can be initialized."""
        executor = AgentExecutor()
        assert executor is not None

    @pytest.mark.anyio
    async def test_build_prompt_strips_mention(self):
        """Test that @resenhazord is stripped from prompt."""
        executor = AgentExecutor()
        prompt = executor._build_prompt("@resenhazord ver placar")

        assert "@resenhazord" not in prompt
        assert "ver placar" in prompt

    @pytest.mark.anyio
    async def test_build_prompt_includes_tools(self):
        """Test that prompt includes command list."""
        executor = AgentExecutor()
        prompt = executor._build_prompt("test")

        assert "command_list" in prompt or "placar" in prompt.lower()

    @pytest.mark.anyio
    async def test_fallback_returns_menu(self):
        """Test fallback returns ,menu command."""
        data = CommandData(
            text="@resenhazord blah",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        result = executor._fallback(data)

        assert result.text == ",menu"


class TestCommandMapping:
    @pytest.mark.anyio
    async def test_build_command_data(self):
        """Test command data is built correctly."""
        data = CommandData(
            text="@resenhazord ver placar",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        result = executor._build_command_data(data, "placar", '{"now": true}')

        assert result.text == ",placar --now"

    @pytest.mark.anyio
    async def test_build_command_data_with_args(self):
        """Test command data with text args."""
        data = CommandData(
            text="@resenhazord buscar música",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        result = executor._build_command_data(data, "music", "")

        assert result.text == ",music"