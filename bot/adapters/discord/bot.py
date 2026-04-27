import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, ClassVar

import aiohttp
import discord
import structlog
from discord import app_commands

from bot.adapters.discord.agent_router import DiscordAgentRouter
from bot.adapters.discord.handler import DiscordInteractionHandler
from bot.adapters.discord.renderer import DiscordResponseRenderer
from bot.adapters.discord.slash_register import DiscordSlashRegistrar

logger = structlog.get_logger()

OnMessageCallback = Callable[[discord.Message], Coroutine[Any, Any, None]]


class DiscordBot:
    MAX_SYNC_RETRIES: ClassVar[int] = 5
    SYNC_RETRY_DELAY_SECS: ClassVar[float] = 3.0

    def __init__(self, guild_id: str) -> None:
        self._guild = discord.Object(id=int(guild_id))
        intents = discord.Intents(guilds=True, messages=True, message_content=True)
        self._client = discord.Client(intents=intents)
        self._tree = app_commands.CommandTree(self._client)
        self._handler = DiscordInteractionHandler()
        self._renderer = DiscordResponseRenderer()
        self._router = DiscordAgentRouter(self._renderer)
        self._registrar = DiscordSlashRegistrar(self._tree, self._handler)
        self._setup_events()

    @property
    def client(self) -> discord.Client:
        return self._client

    def register_commands(self) -> None:
        self._registrar.register_all()

    def _setup_events(self) -> None:
        client = self._client
        guild = self._guild

        client.event(self._make_on_ready())
        client.event(self._make_on_message(client, guild))

    def _make_on_ready(self) -> Callable[[], Coroutine[Any, Any, None]]:
        client = self._client
        guild = self._guild
        tree = self._tree

        async def on_ready() -> None:
            await self._sync_with_retries(client, tree, guild)

        return on_ready

    def _make_on_message(self, client: discord.Client, guild: discord.Object) -> OnMessageCallback:
        router = self._router

        async def on_message(message: discord.Message) -> None:
            if message.author == client.user or not message.content:
                return
            if message.guild is None:
                await router.handle_dm(message)
                return
            if message.guild.id != guild.id:
                return
            if not self._mentions_bot(client, message):
                return
            await router.handle_mention(message)

        return on_message

    @staticmethod
    def _mentions_bot(client: discord.Client, message: discord.Message) -> bool:
        app_user = client.user
        if app_user is None:
            return False
        bot_mention = f'<@{app_user.id}>'
        return bot_mention in message.content or f'@{app_user.name}' in message.content

    async def _sync_with_retries(
        self,
        client: discord.Client,
        tree: app_commands.CommandTree,
        guild: discord.Object,
    ) -> None:
        for attempt in range(1, self.MAX_SYNC_RETRIES + 1):
            try:
                synced = await tree.sync()
            except aiohttp.ClientConnectorError:
                if attempt == self.MAX_SYNC_RETRIES:
                    logger.exception('discord_sync_failed', guild_id=guild.id, attempts=attempt)
                    return
                delay = self.SYNC_RETRY_DELAY_SECS * attempt
                logger.warning(
                    'discord_sync_retry',
                    guild_id=guild.id,
                    attempt=attempt,
                    retry_in=delay,
                )
                await asyncio.sleep(delay)
                continue
            logger.info(
                'discord_connected',
                tag=str(client.user),
                synced_commands=[c.name for c in synced],
            )
            return
