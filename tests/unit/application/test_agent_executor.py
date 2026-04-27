"""Tests for Agent Executor."""

import pytest

from bot.application.agent_executor import AgentExecutor
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.providers.base import LLMResponse


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
        prompt = executor._build_prompt('@resenhazord ver placar')

        assert '@resenhazord' not in prompt
        assert 'ver placar' in prompt

    @pytest.mark.anyio
    async def test_build_prompt_includes_tools(self):
        """Test that prompt includes command list."""
        executor = AgentExecutor()
        prompt = executor._build_prompt('test')

        assert 'command_list' in prompt or 'placar' in prompt.lower()

    @pytest.mark.anyio
    async def test_fallback_returns_empty(self):
        """Test fallback returns empty text (no response)."""
        data = CommandData(
            text='@resenhazord blah',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        result = executor._fallback(data)

        assert result.text == ''

    @pytest.mark.anyio
    async def test_fallback_preserves_media_fields(self):
        """Test fallback preserves media fields from original data."""
        data = CommandData(
            text='@resenhazord blah',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
            media_is_animated=False,
            media_caption='test image',
        )
        executor = AgentExecutor()

        result = executor._fallback(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'
        assert result.media_caption == 'test image'

    @pytest.mark.anyio
    async def test_build_command_data_preserves_media_fields(self):
        """Test _build_command_data preserves media fields."""
        data = CommandData(
            text='make sticker',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
            media_is_animated=False,
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'stic', '')

        assert result.text == ',stic'
        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'

    @pytest.mark.anyio
    async def test_agent_parses_natural_language_to_command(self, mocker):
        """Test agent maps natural language to command via tool call."""
        data = CommandData(
            text='@resenhazord mostrar placar dos jogos',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        mock_chain = mocker.Mock()
        mock_chain.complete = mocker.AsyncMock(
            return_value=LLMResponse(
                content='',
                provider='github',
                model='gpt-4o',
                tool_call={'name': 'placar', 'arguments': '{"now": true}'},
            )
        )
        mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)

        result = await executor.run(data)

        assert result.text == ',placar now'


class TestCommandMapping:
    @pytest.mark.anyio
    async def test_build_command_data(self):
        """Test command data is built correctly."""
        data = CommandData(
            text='@resenhazord ver placar',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'placar', '{"now": true}')

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_build_command_data_with_text_args(self):
        """Regression: text args should be appended after flags.

        Previously the agent used 'args' field but it was ignored, causing
        commands like audio to fail. Now 'args' is appended to command text.
        """
        data = CommandData(
            text='@resenhazord áudio',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'áudio', '{"args": "hello world"}')

        assert result.text == ',áudio hello world'

    @pytest.mark.anyio
    async def test_build_command_data_with_flags_and_args(self):
        """Test command with both flags and text args."""
        data = CommandData(
            text='@resenhazord áudio',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'áudio', '{"dm": true, "args": "test text"}')

        assert 'dm' in result.text
        assert 'test text' in result.text

    @pytest.mark.anyio
    async def test_build_command_data_with_false_flags(self):
        """Test command data with false flags are omitted."""
        data = CommandData(
            text='@resenhazord teste',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'test', '{"verbose": false, "debug": true}')

        assert result.text == ',test debug'

    @pytest.mark.anyio
    async def test_build_command_data_with_empty_args(self):
        """Test command data with empty args."""
        data = CommandData(
            text='@resenhazord ola',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'oi', '')

        assert result.text == ',oi'

    @pytest.mark.anyio
    async def test_build_command_data_excludes_command_key(self):
        """Regression: agent JSON should not include 'command' key in output.

        LLM tool calls include {"command": "tabela", "liga": "br"} but 'command'
        should be filtered out to avoid duplicate in text like ",tabela command tabela liga br".
        """
        data = CommandData(
            text='@resenhazord ver tabela do brasil',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )
        executor = AgentExecutor()

        result = executor._translator.translate(
            data, 'tabela', '{"command": "tabela", "liga": "br"}'
        )

        assert 'command' not in result.text
        assert ',tabela' in result.text
        assert 'br' in result.text

    @pytest.mark.anyio
    async def test_build_command_data_dm_mode_in_group(self):
        """When user requests DM in group, respond via DM (change jid to sender)."""
        data = CommandData(
            text='@resenhazord ver placar privado',
            jid='test@g.us',
            sender_jid='user@s.whatsapp.net',
            is_group=True,
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'placar', '{"now": true}')

        assert result.jid == 'user@s.whatsapp.net'
        assert result.is_group is True

    @pytest.mark.anyio
    async def test_build_command_data_dm_ignored_in_private(self):
        """DM keyword ignored in private chat (not a group)."""
        data = CommandData(
            text='@resenhazord ver placar privado',
            jid='user@s.whatsapp.net',
            sender_jid='user@s.whatsapp.net',
            is_group=False,
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'placar', '{"now": true}')

        assert result.jid == 'user@s.whatsapp.net'

    @pytest.mark.anyio
    async def test_build_command_data_strips_dashes_from_flags(self):
        """Flags like --g4 should become g4 (no dashes)."""
        data = CommandData(
            text='@resenhazord ver tabela br g4',
            jid='test@g.us',
            sender_jid='user@s.whatsapp.net',
            is_group=True,
        )
        executor = AgentExecutor()

        result = executor._translator.translate(data, 'tabela', '{"g4": true}')

        assert 'g4' in result.text
        assert '--' not in result.text


class TestSuggestPrefix:
    """Tests for SUGGEST prefix handling in agent executor."""

    @pytest.mark.anyio
    async def test_run_with_suggest_prefix_returns_suggest_command(self, mocker):
        """Test that SUGGEST: prefix returns suggest command data."""
        data = CommandData(
            text='@resenhazord qual a fundação do flamengo',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        mock_chain = mocker.Mock()
        suggest_content = (
            'SUGGEST: Não sei te dizer a data exata, '
            'mas posso te mandar um time aleatório! Use ,time'
        )
        mock_chain.complete = mocker.AsyncMock(
            return_value=LLMResponse(
                content=suggest_content,
                provider='github',
                model='gpt-4o',
                tool_call=None,
            )
        )
        mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)

        result = await executor.run(data)

        assert result.text.startswith(',suggest:')
        assert 'Não sei' in result.text
        assert 'time' in result.text

    @pytest.mark.anyio
    async def test_run_with_clarify_prefix_returns_clarify_command(self, mocker):
        """Test that CLARIFY: prefix returns clarify command data."""
        data = CommandData(
            text='@resenhazord qual a tabela do brasileiro',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
        )
        executor = AgentExecutor()

        mock_chain = mocker.Mock()
        mock_chain.complete = mocker.AsyncMock(
            return_value=LLMResponse(
                content='CLARIFY: Você quer ver a tabela de qual competição?',
                provider='github',
                model='gpt-4o',
                tool_call=None,
            )
        )
        mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)

        result = await executor.run(data)

        assert result.text.startswith(',clarify:')
        assert 'tabela' in result.text.lower()

    @pytest.mark.anyio
    async def test_build_prompt_includes_context_when_quoted(self):
        """Test that quoted_text is included in prompt context."""
        executor = AgentExecutor()
        prompt = executor._build_prompt(
            'sim',
            context='Não sei te dizer..., use ,time',
        )

        assert 'Contexto da mensagem anterior' in prompt
        assert ',time' in prompt

    @pytest.mark.anyio
    async def test_build_prompt_no_context_when_not_quoted(self):
        """Test that prompt has no context block when quoted_text is None."""
        executor = AgentExecutor()
        prompt = executor._build_prompt('me mande um fato')

        assert 'Contexto da mensagem anterior' not in prompt

    @pytest.mark.anyio
    async def test_run_preserves_media_fields_on_suggest(self, mocker):
        """Test that media fields are preserved when returning suggest."""
        data = CommandData(
            text='make sticker',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            media_type='image',
            media_source='https://example.com/image.jpg',
        )
        executor = AgentExecutor()

        mock_chain = mocker.Mock()
        mock_chain.complete = mocker.AsyncMock(
            return_value=LLMResponse(
                content='SUGGEST: Não posso fazer sticker dessa imagem, use ,carro!',
                provider='github',
                model='gpt-4o',
                tool_call=None,
            )
        )
        mocker.patch.object(ProviderChain, 'instance', return_value=mock_chain)

        result = await executor.run(data)

        assert result.media_type == 'image'
        assert result.media_source == 'https://example.com/image.jpg'
