from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.adapters.discord.handler import DiscordInteractionHandler
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


@pytest.fixture
def handler():
    return DiscordInteractionHandler()


@pytest.fixture
def port():
    port = AsyncMock()
    port.send_response = AsyncMock()
    port.send_followup = AsyncMock()
    return port


class TestHandle:
    @pytest.mark.anyio
    async def test_calls_send_response_with_dice_roll(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = AsyncMock()
        strategy.run = AsyncMock(
            return_value=[
                BotMessage(jid='111222333', content=TextContent(text='Aqui está sua rolada: 7 🎲'))
            ]
        )
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_response.assert_called_once_with('Aqui está sua rolada: 7 🎲')

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

    @pytest.mark.anyio
    async def test_no_match_sends_error_response(self, handler, port, mocker):
        interaction = make_interaction(command_name='unknown')
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=None)),
        )

        await handler.handle(port, interaction)

        port.send_response.assert_called_once()
        assert 'reconhecido' in port.send_response.call_args[0][0]

    @pytest.mark.anyio
    async def test_command_exception_sends_error_response(self, handler, port, mocker):
        interaction = make_interaction()
        strategy = MagicMock()
        strategy.run = AsyncMock(side_effect=RuntimeError('boom'))
        mocker.patch(
            'bot.adapters.discord.handler.CommandRegistry.instance',
            return_value=MagicMock(get_strategy=MagicMock(return_value=strategy)),
        )

        await handler.handle(port, interaction)

        port.send_response.assert_called_once()
        assert 'erro' in port.send_response.call_args[0][0]

    @pytest.mark.anyio
    async def test_no_command_name_returns_early(self, handler, port, mocker):
        interaction = make_interaction()
        interaction.command = None
        mocker.patch('bot.adapters.discord.handler.CommandRegistry.instance')

        await handler.handle(port, interaction)

        port.send_response.assert_not_called()
