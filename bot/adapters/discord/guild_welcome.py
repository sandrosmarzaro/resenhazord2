import discord
import structlog

from bot.data.welcome_messages import DISCORD_WELCOME

logger = structlog.get_logger()


class DiscordGuildWelcome:
    # Named for the discord.py event, so client.event() registers it as-is.
    async def on_guild_join(self, guild: discord.Guild) -> None:
        channel = self._writable_channel(guild)
        if channel is None:
            logger.info('discord_guild_welcome_skipped', guild_id=guild.id)
            return
        await channel.send(DISCORD_WELCOME)

    @staticmethod
    def _writable_channel(guild: discord.Guild) -> discord.TextChannel | None:
        candidates = [guild.system_channel, *guild.text_channels]
        return next(
            (
                channel
                for channel in candidates
                if channel is not None and channel.permissions_for(guild.me).send_messages
            ),
            None,
        )
