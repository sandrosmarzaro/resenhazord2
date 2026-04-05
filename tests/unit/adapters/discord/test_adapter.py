import discord
import pytest

from bot.adapters.discord.adapter import DiscordInteractionAdapter


@pytest.fixture
def interaction(mocker):
    interaction = mocker.MagicMock()
    interaction.response = mocker.MagicMock()
    interaction.response.send_message = mocker.AsyncMock()
    interaction.response.defer = mocker.AsyncMock()
    interaction.followup = mocker.MagicMock()
    interaction.followup.send = mocker.AsyncMock()
    return interaction


@pytest.fixture
def adapter(interaction):
    return DiscordInteractionAdapter(interaction)


class TestIsDeferred:
    def test_starts_false(self, adapter):
        assert adapter.is_deferred is False

    @pytest.mark.anyio
    async def test_true_after_defer(self, adapter):
        await adapter.defer()

        assert adapter.is_deferred is True


class TestSendMessage:
    @pytest.mark.anyio
    async def test_text_only(self, adapter, interaction):
        await adapter.send_message('hello')

        interaction.response.send_message.assert_called_once_with(content='hello')

    @pytest.mark.anyio
    async def test_embed_only(self, adapter, interaction):
        embed = discord.Embed(description='test')

        await adapter.send_message(embed=embed)

        interaction.response.send_message.assert_called_once_with(embed=embed)

    @pytest.mark.anyio
    async def test_file_only(self, adapter, interaction, mocker):
        file = mocker.MagicMock(spec=discord.File)

        await adapter.send_message(file=file)

        interaction.response.send_message.assert_called_once_with(file=file)

    @pytest.mark.anyio
    async def test_all_three(self, adapter, interaction, mocker):
        embed = discord.Embed()
        file = mocker.MagicMock(spec=discord.File)

        await adapter.send_message('text', embed=embed, file=file)

        interaction.response.send_message.assert_called_once_with(
            content='text', embed=embed, file=file
        )

    @pytest.mark.anyio
    async def test_deferred_routes_to_followup(self, adapter, interaction):
        await adapter.defer()

        await adapter.send_message('follow up')

        interaction.response.send_message.assert_not_called()
        interaction.followup.send.assert_called_once_with(content='follow up')


class TestDefer:
    @pytest.mark.anyio
    async def test_delegates_to_interaction_response(self, adapter, interaction):
        await adapter.defer()

        interaction.response.defer.assert_called_once()


class TestSendFollowup:
    @pytest.mark.anyio
    async def test_text_only(self, adapter, interaction):
        await adapter.send_followup('follow up text')

        interaction.followup.send.assert_called_once_with(content='follow up text')

    @pytest.mark.anyio
    async def test_embed_only(self, adapter, interaction):
        embed = discord.Embed(description='test')

        await adapter.send_followup(embed=embed)

        interaction.followup.send.assert_called_once_with(embed=embed)

    @pytest.mark.anyio
    async def test_file_only(self, adapter, interaction, mocker):
        file = mocker.MagicMock(spec=discord.File)

        await adapter.send_followup(file=file)

        interaction.followup.send.assert_called_once_with(file=file)

    @pytest.mark.anyio
    async def test_all_three(self, adapter, interaction, mocker):
        embed = discord.Embed()
        file = mocker.MagicMock(spec=discord.File)

        await adapter.send_followup('text', embed=embed, file=file)

        interaction.followup.send.assert_called_once_with(content='text', embed=embed, file=file)
