from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.adapters.discord.adapter import DiscordInteractionAdapter


def make_interaction() -> MagicMock:
    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def interaction():
    return make_interaction()


@pytest.fixture
def adapter(interaction):
    return DiscordInteractionAdapter(interaction)


class TestSendResponse:
    @pytest.mark.anyio
    async def test_delegates_to_interaction_response(self, adapter, interaction):
        await adapter.send_response('hello')

        interaction.response.send_message.assert_called_once_with('hello')


class TestDefer:
    @pytest.mark.anyio
    async def test_delegates_to_interaction_response(self, adapter, interaction):
        await adapter.defer()

        interaction.response.defer.assert_called_once()


class TestSendFollowup:
    @pytest.mark.anyio
    async def test_delegates_to_followup(self, adapter, interaction):
        await adapter.send_followup('follow up text')

        interaction.followup.send.assert_called_once_with('follow up text')
