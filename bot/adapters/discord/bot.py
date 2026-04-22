import asyncio
import inspect
import io
import re
import unicodedata
from typing import Any, ClassVar, cast

import aiohttp
import discord
import structlog
from discord import app_commands

from bot.adapters.discord.adapter import DiscordInteractionAdapter
from bot.adapters.discord.handler import DiscordInteractionHandler
from bot.application.agent_executor import AgentExecutor
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import ArgType, Command, CommandConfig, Flag, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.contents.image_content import (
    ImageBufferContent,
    ImageContent,
)
from bot.domain.models.contents.text_content import TextContent

logger = structlog.get_logger()


class DiscordBot:
    DISCORD_NAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'[^a-z0-9_-]')
    DISCORD_NAME_MAX_LENGTH: ClassVar[int] = 32
    DISCORD_DESC_MAX_LENGTH: ClassVar[int] = 100
    WHATSAPP_ONLY_FLAGS: ClassVar[frozenset[str]] = frozenset({Flag.DM, Flag.SHOW})
    MAX_SYNC_RETRIES: ClassVar[int] = 5
    SYNC_RETRY_DELAY_SECS: ClassVar[float] = 3.0

    def __init__(self, guild_id: str) -> None:
        self._guild = discord.Object(id=int(guild_id))
        intents = discord.Intents(guilds=True, messages=True, message_content=True)
        self._client = discord.Client(intents=intents)
        self._tree = app_commands.CommandTree(self._client)
        self._handler = DiscordInteractionHandler()
        self._setup_events()

    @property
    def client(self) -> discord.Client:
        return self._client

    def register_commands(self) -> None:
        for command in CommandRegistry.instance().get_all():
            if Platform.DISCORD not in command.config.platforms:
                continue
            self._register_slash_command(command)
            for alias in command.config.aliases:
                self._register_alias(command, alias)
            logger.info('discord_command_registered', name=command.config.name)

    def _register_slash_command(self, command: Command) -> None:
        config = command.config
        discord_name = self._normalize_name(config.name)
        self._handler.register_name(discord_name, f',{config.name}')
        self._do_register(discord_name, command)

    def _register_alias(self, command: Command, alias: str) -> None:
        discord_name = self._normalize_name(alias)
        self._handler.register_name(discord_name, f',{alias}')
        self._do_register(discord_name, command)

    def _do_register(self, discord_name: str, command: Command) -> None:
        existing = self._tree.get_command(discord_name, guild=self._guild)
        if existing:
            logger.debug('command_already_registered', name=discord_name)
            return

        config = command.config
        description = command.menu_description[: self.DISCORD_DESC_MAX_LENGTH]

        callback = self._make_callback()
        cast('Any', callback).__signature__ = self._build_signature(config)

        slash_cmd = app_commands.Command(
            name=discord_name,
            description=description,
            callback=callback,  # type: ignore[arg-type]
        )

        for opt in config.options:
            if opt.name not in slash_cmd._params:
                continue
            if opt.values:
                slash_cmd._params[opt.name].choices = [
                    app_commands.Choice(name=v, value=v) for v in opt.values
                ]
            if opt.description:
                slash_cmd._params[opt.name].description = opt.description

        if 'args' in slash_cmd._params and config.args_label:
            slash_cmd._params['args'].description = config.args_label

        self._tree.add_command(slash_cmd, guild=self._guild)

    def _make_callback(self):
        handler = self._handler

        async def callback(interaction: discord.Interaction, **kwargs) -> None:
            port = DiscordInteractionAdapter(interaction)
            await handler.handle(port, interaction, **kwargs)

        return callback

    @classmethod
    def _build_signature(cls, config: CommandConfig) -> inspect.Signature:
        params: list[inspect.Parameter] = [
            inspect.Parameter(
                'interaction',
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=discord.Interaction,
            ),
        ]

        params.extend(
            inspect.Parameter(
                opt.name,
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=str | None,
            )
            for opt in config.options
            if opt.values or opt.pattern
        )

        for flag in config.flags:
            if flag in cls.WHATSAPP_ONLY_FLAGS:
                continue
            params.append(
                inspect.Parameter(
                    flag,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=None,
                    annotation=bool | None,
                )
            )

        if config.args != ArgType.NONE:
            default = inspect.Parameter.empty if config.args == ArgType.REQUIRED else None
            annotation = str if config.args == ArgType.REQUIRED else (str | None)
            params.append(
                inspect.Parameter(
                    'args',
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )

        return inspect.Signature(params)

    @classmethod
    def _normalize_name(cls, name: str) -> str:
        normalized = unicodedata.normalize('NFD', name.lower())
        ascii_only = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        cleaned = cls.DISCORD_NAME_PATTERN.sub('', ascii_only.replace(' ', '-'))
        return cleaned[: cls.DISCORD_NAME_MAX_LENGTH]

    def _setup_events(self) -> None:
        client = self._client
        tree = self._tree
        guild = self._guild

        @client.event
        async def on_ready() -> None:
            for attempt in range(1, self.MAX_SYNC_RETRIES + 1):
                try:
                    synced = await tree.sync(guild=guild)
                except aiohttp.ClientConnectorError:
                    if attempt == self.MAX_SYNC_RETRIES:
                        logger.exception(
                            'discord_sync_failed',
                            guild_id=guild.id,
                            attempts=attempt,
                        )
                        return
                    delay = self.SYNC_RETRY_DELAY_SECS * attempt
                    logger.warning(
                        'discord_sync_retry',
                        guild_id=guild.id,
                        attempt=attempt,
                        retry_in=delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.info(
                        'discord_connected',
                        tag=str(client.user),
                        guild_id=guild.id,
                        synced_commands=[c.name for c in synced],
                    )
                    return

        @client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == client.user:
                return
            if not message.content:
                return
            if not message.guild or message.guild.id != guild.id:
                return

            app_user = client.user
            if app_user is None:
                return

            bot_mention = f'<@{app_user.id}>'
            if bot_mention not in message.content and f'@{app_user.name}' not in message.content:
                return

            logger.info('discord_agent_mention', text=message.content)

            try:
                executor = AgentExecutor(CommandRegistry.instance())
                data = CommandData(
                    text=message.content,
                    jid=str(message.channel.id),
                    sender_jid=str(message.author.id),
                    is_group=True,
                    platform='discord',
                )
                result = await executor.run(data)

                strategy = CommandRegistry.instance().get_strategy(result.text)
                if strategy is None:
                    await message.reply('Comando não reconhecido.')
                    return

                command_data = CommandData(
                    text=result.text,
                    jid=data.jid,
                    sender_jid=data.sender_jid,
                    participant=data.participant,
                    is_group=data.is_group,
                    mentioned_jids=data.mentioned_jids,
                    quoted_message_id=data.quoted_message_id,
                    message_id=data.message_id,
                    platform='discord',
                )

                messages = await strategy.run(command_data)

                if not messages:
                    await message.reply('Sem resposta do comando.')
                    return

                for msg in messages:
                    content = msg.content
                    if isinstance(content, ImageBufferContent):
                        file = discord.File(
                            io.BytesIO(content.data),
                            filename='image.jpg',
                        )
                        await message.reply(content.caption or '📷', file=file)
                    elif isinstance(content, ImageContent):
                        if content.url:
                            embed = discord.Embed()
                            embed.set_image(url=content.url)
                            await message.reply(content.caption or '📷', embed=embed)
                        else:
                            await message.reply(content.caption or '📷')
                    elif isinstance(content, VideoContent):
                        if content.url:
                            await message.reply(content.caption or '🎬', suppress_embeds=False)
                            await message.reply(content.url)
                        else:
                            await message.reply(content.caption or '🎬')
                    elif isinstance(content, TextContent):
                        text = content.text
                        max_chunk = 2000
                        if len(text) > max_chunk:
                            for i in range(0, len(text), max_chunk):
                                chunk = text[i : i + max_chunk]
                                await message.reply(chunk)
                        else:
                            await message.reply(text)
            except Exception:
                logger.exception('discord_agent_error')
                await message.reply('Erro ao processar comando.')
