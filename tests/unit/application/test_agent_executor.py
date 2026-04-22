"""Tests for Agent Executor."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from bot.application.agent_executor import AgentExecutor
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.provider_chain import LLMResponse


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

    @pytest.mark.anyio
    async def test_agent_parses_natural_language_to_command(self):
        """Test agent maps natural language to command via tool call."""
        data = CommandData(
            text="@resenhazord mostrar placar dos jogos",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        # Mock the provider chain to return a tool call
        mock_chain = Mock()
        mock_chain.complete = AsyncMock(
            return_value=LLMResponse(
                content="",
                provider="github",
                model="gpt-4o",
                tool_call={"name": "placar", "arguments": '{"now": true}'},
            )
        )

        with patch("bot.application.agent_executor.get_chain", return_value=mock_chain):
            result = await executor.run(data)

        assert result.text == ",placar now"

    @pytest.mark.anyio
    async def test_agent_clears_memory_after_execution(self):
        """Test agent clears memory (no-op for single-turn)."""
        data = CommandData(
            text="@resenhazord teste",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        # _clear_memory is a no-op, just ensure it doesn't raise
        await executor.run(data)
        executor._clear_memory()  # Should not raise


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

        assert result.text == ",placar now"

    @pytest.mark.anyio
    async def test_build_command_data_with_text_args(self):
        """Regression: text args should be appended after flags.

        Previously the agent used 'args' field but it was ignored, causing
        commands like audio to fail. Now 'args' is appended to command text.
        """
        data = CommandData(
            text="@resenhazord áudio",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        result = executor._build_command_data(data, "áudio", '{"args": "hello world"}')

        assert result.text == ",áudio hello world"

    @pytest.mark.anyio
    async def test_build_command_data_with_flags_and_args(self):
        """Test command with both flags and text args."""
        data = CommandData(
            text="@resenhazord áudio",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        result = executor._build_command_data(
            data, "áudio", '{"dm": true, "args": "test text"}'
        )

        assert "dm" in result.text
        assert "test text" in result.text

    @pytest.mark.anyio
    async def test_build_command_data_with_false_flags(self):
        """Test command data with false flags are omitted."""
        data = CommandData(
            text="@resenhazord teste",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        result = executor._build_command_data(data, "test", '{"verbose": false, "debug": true}')

        assert result.text == ",test debug"

    @pytest.mark.anyio
    async def test_build_command_data_with_empty_args(self):
        """Test command data with empty args."""
        data = CommandData(
            text="@resenhazord ola",
            jid="test@g.us",
            sender_jid="test@s.whatsapp.net",
        )
        executor = AgentExecutor()

        result = executor._build_command_data(data, "oi", "")

        assert result.text == ",oi"


