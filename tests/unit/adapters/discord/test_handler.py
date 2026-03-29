from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bot.adapters.discord.handler import DiscordInteractionHandler
from bot.domain.commands.base import ArgType, Command, CommandConfig, CommandScope, OptionDef
from bot.domain.exceptions import BotError
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage

if TYPE_CHECKING:
    from bot.domain.models.command_data import CommandData


def make_interaction(
    command_name: str = 'd20',
    channel_id: int = 111222333,
    user_id: int = 999888777,
    guild_id: int | None = 1234567890,
    display_name: str = 'TestUser',
) -> MagicMock:
    interaction = MagicMock()
    interaction.command = MagicMock()
    interaction.command.name = command_name
    interaction.channel_id = channel_id
    interaction.user = MagicMock()
    interaction.user.id = user_id
    interaction.user.display_name = display_name
    interaction.id = 555666777
    interaction.guild_id = guild_id
    return interaction


def make_strategy(messages: list[BotMessage]) -> MagicMock:
    strategy = MagicMock()
    strategy.run = AsyncMock(return_value=messages)
    return strategy


@pytest.fixture
def handler():
    return DiscordInteractionHandler()


@pytest.fixture
def port():
    port = AsyncMock()
    port.send_message = AsyncMock()
    port.send_followup = AsyncMock()
    port.defer = AsyncMock()
    port.is_deferred = False
    return port


class TestHandle:
    @pytest.mark.anyio
    async def test_defers_before_executing(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = make_strategy([BotMessage(jid='111', content=TextContent(text='roll: 7'))])
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.defer.assert_called_once()

    @pytest.mark.anyio
    async def test_text_command_sends_followup(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = make_strategy(
            [BotMessage(jid='111', content=TextContent(text='Aqui esta sua rolada: 7 🎲'))]
        )
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_followup.assert_called_once_with(
            'Aqui esta sua rolada: 7 🎲', embed=None, file=None
        )

    @pytest.mark.anyio
    async def test_image_command_sends_embed(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = make_strategy(
            [BotMessage(jid='111', content=ImageContent(url='https://example.com/img.jpg'))]
        )
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )
        mock_response = MagicMock()
        mock_response.content = b'image-bytes'
        mocker.patch('bot.adapters.discord.handler.HttpClient.get', return_value=mock_response)

        await handler.handle(port, interaction)

        call_kwargs = port.send_followup.call_args
        assert call_kwargs.kwargs['embed'] is not None
        assert call_kwargs.kwargs['file'] is not None
        assert call_kwargs.args[0] is None

    @pytest.mark.anyio
    async def test_no_command_name_returns_early(self, handler, port, mocker):
        interaction = make_interaction()
        interaction.command = None
        mocker.patch('bot.adapters.discord.handler.CommandRegistry.instance')

        await handler.handle(port, interaction)

        port.send_message.assert_not_called()
        port.defer.assert_not_called()

    @pytest.mark.anyio
    async def test_no_match_sends_error(self, handler, port, mocker):
        interaction = make_interaction(command_name='unknown')
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=None)),
        )

        await handler.handle(port, interaction)

        port.send_message.assert_called_once()
        assert 'reconhecido' in port.send_message.call_args[0][0]

    @pytest.mark.anyio
    async def test_bot_error_sends_user_message(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = MagicMock()
        strategy.run = AsyncMock(side_effect=BotError('Erro amigavel'))
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_followup.assert_called_once_with('Erro amigavel')

    @pytest.mark.anyio
    async def test_generic_error_sends_fallback(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = MagicMock()
        strategy.run = AsyncMock(side_effect=RuntimeError('boom'))
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_followup.assert_called_once()
        assert 'erro' in port.send_followup.call_args[0][0]

    @pytest.mark.anyio
    async def test_empty_messages_sends_no_response(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = make_strategy([])
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_followup.assert_called_once()
        assert 'resposta' in port.send_followup.call_args[0][0]

    @pytest.mark.anyio
    async def test_builds_command_data_correctly(self, handler, port, mocker):
        interaction = make_interaction(
            command_name='d20',
            channel_id=111,
            user_id=999,
            guild_id=777,
            display_name='Alice',
        )
        interaction.id = 555
        captured: list[CommandData] = []
        strategy = MagicMock()
        strategy.run = AsyncMock(
            side_effect=lambda data: (
                captured.append(data)  # type: ignore[arg-type]
                or [BotMessage(jid='111', content=TextContent(text='ok'))]
            ),
        )
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        assert len(captured) == 1
        data = captured[0]
        assert data.text == ',d20'
        assert data.jid == '111'
        assert data.sender_jid == '999'
        assert data.message_id == '555'
        assert data.is_group is True
        assert data.push_name == 'Alice'

    @pytest.mark.anyio
    async def test_is_group_false_when_no_guild(self, handler, port, mocker):
        interaction = make_interaction(guild_id=None)
        captured: list[CommandData] = []
        strategy = MagicMock()
        strategy.config.group_only = False
        strategy.config.scope = 'public'
        strategy.run = AsyncMock(
            side_effect=lambda data: (
                captured.append(data)  # type: ignore[arg-type]
                or [BotMessage(jid='111', content=TextContent(text='ok'))]
            ),
        )
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        assert captured[0].is_group is False


class TestBuildCommandText:
    def _make_strategy(self, config: CommandConfig) -> MagicMock:
        strategy = MagicMock(spec=Command)
        strategy.config = config
        return strategy

    def _make_handler(self, strategy: MagicMock | None, mocker) -> DiscordInteractionHandler:
        handler = DiscordInteractionHandler()
        registry = MagicMock()
        registry.get_strategy = MagicMock(return_value=strategy)
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=registry,
        )
        return handler

    def test_simple_command(self, mocker):
        config = CommandConfig(name='d20')
        strategy = self._make_strategy(config)
        handler = self._make_handler(strategy, mocker)

        result = handler._build_command_text('d20', {})

        assert result == ',d20'

    def test_command_with_args(self, mocker):
        config = CommandConfig(name='horoscopo', args=ArgType.OPTIONAL)
        strategy = self._make_strategy(config)
        handler = self._make_handler(strategy, mocker)

        result = handler._build_command_text('horoscopo', {'args': 'leao'})

        assert result == ',horoscopo leao'

    def test_command_with_option(self, mocker):
        config = CommandConfig(
            name='stic',
            options=[OptionDef(name='type', values=['crop', 'full', 'circle', 'rounded'])],
        )
        strategy = self._make_strategy(config)
        handler = self._make_handler(strategy, mocker)

        result = handler._build_command_text('stic', {'type': 'crop'})

        assert result == ',stic crop'

    def test_command_with_flag_true(self, mocker):
        config = CommandConfig(name='bandeira', flags=['detail'])
        strategy = self._make_strategy(config)
        handler = self._make_handler(strategy, mocker)

        result = handler._build_command_text('bandeira', {'detail': True})

        assert result == ',bandeira detail'

    def test_command_with_flag_none_skipped(self, mocker):
        config = CommandConfig(name='bandeira', flags=['detail'])
        strategy = self._make_strategy(config)
        handler = self._make_handler(strategy, mocker)

        result = handler._build_command_text('bandeira', {'detail': None})

        assert result == ',bandeira'

    def test_command_with_all(self, mocker):
        config = CommandConfig(
            name='filme',
            options=[OptionDef(name='mode', values=['top', 'popular'])],
            flags=['detail'],
            args=ArgType.OPTIONAL,
        )
        strategy = self._make_strategy(config)
        handler = self._make_handler(strategy, mocker)

        result = handler._build_command_text(
            'filme', {'mode': 'top', 'detail': True, 'args': 'Batman'}
        )

        assert result == ',filme top detail Batman'


class TestNsfwAndGroupOnly:
    def _make_nsfw_strategy(self) -> MagicMock:
        strategy = make_strategy([BotMessage(jid='111', content=TextContent(text='ok'))])
        strategy.config = MagicMock()
        strategy.config.scope = CommandScope.NSFW
        strategy.config.group_only = False
        return strategy

    def _make_group_only_strategy(self) -> MagicMock:
        strategy = make_strategy([BotMessage(jid='111', content=TextContent(text='ok'))])
        strategy.config = MagicMock()
        strategy.config.scope = CommandScope.PUBLIC
        strategy.config.group_only = True
        return strategy

    @pytest.mark.anyio
    async def test_nsfw_in_sfw_channel_blocked(self, handler, port, mocker):
        interaction = make_interaction()
        interaction.channel = MagicMock()
        interaction.channel.nsfw = False
        strategy = self._make_nsfw_strategy()
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_followup.assert_called_once()
        assert 'NSFW' in port.send_followup.call_args[0][0]

    @pytest.mark.anyio
    async def test_nsfw_in_nsfw_channel_allowed(self, handler, port, mocker):
        interaction = make_interaction()
        interaction.channel = MagicMock()
        interaction.channel.nsfw = True
        strategy = self._make_nsfw_strategy()
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        strategy.run.assert_called_once()

    @pytest.mark.anyio
    async def test_group_only_in_dm_blocked(self, handler, port, mocker):
        interaction = make_interaction(guild_id=None)
        strategy = self._make_group_only_strategy()
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_message.assert_called_once()
        assert 'servidores' in port.send_message.call_args[0][0]
        strategy.run.assert_not_called()


class TestRegisterName:
    def test_register_name_maps_discord_to_registry(self):
        handler = DiscordInteractionHandler()
        handler.register_name('rule-34', ',rule 34')
        assert handler._name_map['rule-34'] == ',rule 34'

    def test_build_command_text_uses_name_map(self, mocker):
        handler = DiscordInteractionHandler()
        handler.register_name('rule-34', ',rule 34')
        config = CommandConfig(name='rule 34')
        strategy = MagicMock(spec=Command)
        strategy.config = config
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        result = handler._build_command_text('rule-34', {})

        assert result == ',rule 34'

    def test_build_command_text_falls_back_to_prefix_when_not_in_map(self, mocker):
        handler = DiscordInteractionHandler()
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=None)),
        )

        result = handler._build_command_text('d20', {})

        assert result == ',d20'


class TestPreprocessMessages:
    JID = 'test-jid'

    @pytest.mark.anyio
    async def test_audio_content_downloads_and_converts(self, mocker):
        mock_response = MagicMock()
        mock_response.content = b'audio-bytes'
        mocker.patch(
            'bot.adapters.discord.handler.HttpClient.get',
            return_value=mock_response,
        )
        messages = [
            BotMessage(jid=self.JID, content=AudioContent(url='https://tts.example.com/audio'))
        ]

        result = await DiscordInteractionHandler._preprocess_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0].content, AudioBufferContent)
        assert result[0].content.data == b'audio-bytes'
        assert result[0].content.type == 'audio_mp3'

    @pytest.mark.anyio
    async def test_http_image_downloads_and_converts(self, mocker):
        mock_response = MagicMock()
        mock_response.content = b'image-bytes'
        mocker.patch(
            'bot.adapters.discord.handler.HttpClient.get',
            return_value=mock_response,
        )
        messages = [
            BotMessage(
                jid=self.JID,
                content=ImageContent(url='http://gatherer.wizards.com/img.jpg', caption='cap'),
            )
        ]

        result = await DiscordInteractionHandler._preprocess_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0].content, ImageBufferContent)
        assert result[0].content.data == b'image-bytes'
        assert result[0].content.caption == 'cap'

    @pytest.mark.anyio
    async def test_https_image_downloads_and_converts(self, mocker):
        mock_response = MagicMock()
        mock_response.content = b'image-bytes'
        mocker.patch(
            'bot.adapters.discord.handler.HttpClient.get',
            return_value=mock_response,
        )
        messages = [
            BotMessage(jid=self.JID, content=ImageContent(url='https://example.com/img.jpg'))
        ]

        result = await DiscordInteractionHandler._preprocess_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0].content, ImageBufferContent)
        assert result[0].content.data == b'image-bytes'

    @pytest.mark.anyio
    async def test_text_content_passes_through(self, mocker):
        mocker.patch('bot.adapters.discord.handler.HttpClient.get')
        messages = [BotMessage(jid=self.JID, content=TextContent(text='hello'))]

        result = await DiscordInteractionHandler._preprocess_messages(messages)

        assert result == messages

    @pytest.mark.anyio
    async def test_audio_download_failure_falls_back_to_original(self, mocker):
        mocker.patch(
            'bot.adapters.discord.handler.HttpClient.get',
            side_effect=httpx.ConnectError('network error'),
        )
        original = BotMessage(jid=self.JID, content=AudioContent(url='https://broken.com/audio'))
        result = await DiscordInteractionHandler._preprocess_messages([original])

        assert result[0] is original
