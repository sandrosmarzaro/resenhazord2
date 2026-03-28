import discord
import structlog
from discord import app_commands

from bot.adapters.discord.adapter import DiscordInteractionAdapter
from bot.adapters.discord.handler import DiscordInteractionHandler

logger = structlog.get_logger()


def create_discord_bot(guild_id: str) -> discord.Client:
    intents = discord.Intents(guilds=True)
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    handler = DiscordInteractionHandler()
    guild = discord.Object(id=int(guild_id))

    @tree.command(name='d20', description='Role um dado de vinte dimensões.', guild=guild)
    async def d20(interaction: discord.Interaction) -> None:
        port = DiscordInteractionAdapter(interaction)
        await handler.handle(port, interaction)

    @client.event
    async def on_ready() -> None:
        synced = await tree.sync(guild=guild)
        logger.info(
            'discord_connected',
            tag=str(client.user),
            guild_id=guild_id,
            synced_commands=[c.name for c in synced],
        )

    return client
