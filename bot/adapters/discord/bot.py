import inspect
import re
import unicodedata
from typing import Any, ClassVar, cast

import discord
import structlog
from discord import app_commands

from bot.adapters.discord.adapter import DiscordInteractionAdapter
from bot.adapters.discord.handler import DiscordInteractionHandler
from bot.adapters.discord.music.commands import MusicCommands
from bot.adapters.discord.music.views import NowPlayingView
from bot.adapters.discord.music.voice_manager import VoiceManager
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import ArgType, Command, CommandConfig, Flag, Platform

logger = structlog.get_logger()


class DiscordBot:
    DISCORD_NAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'[^a-z0-9_-]')
    DISCORD_NAME_MAX_LENGTH: ClassVar[int] = 32
    DISCORD_DESC_MAX_LENGTH: ClassVar[int] = 100
    WHATSAPP_ONLY_FLAGS: ClassVar[frozenset[str]] = frozenset({Flag.DM, Flag.SHOW})

    def __init__(self, guild_id: str) -> None:
        self._guild = discord.Object(id=int(guild_id))
        self._client = discord.Client(
            intents=discord.Intents(guilds=True, voice_states=True),
        )
        self._tree = app_commands.CommandTree(self._client)
        self._handler = DiscordInteractionHandler()
        self._voice_manager = VoiceManager(view_factory=NowPlayingView)
        self._music_commands = MusicCommands(self._tree, self._guild, self._voice_manager)
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
        self._music_commands.register()
        logger.info('discord_music_commands_registered')

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
        vm = self._voice_manager

        @client.event
        async def on_ready() -> None:
            synced = await tree.sync(guild=guild)
            logger.info(
                'discord_connected',
                tag=str(client.user),
                guild_id=guild.id,
                synced_commands=[c.name for c in synced],
            )

        @client.event
        async def on_voice_state_update(
            member: discord.Member,
            before: discord.VoiceState,
            _after: discord.VoiceState,
        ) -> None:
            if not before.channel or member.id == client.user.id:
                return

            bot_in_channel = client.user in before.channel.members
            if not bot_in_channel:
                return

            non_bot_members = [m for m in before.channel.members if not m.bot]
            if not non_bot_members:
                vm.schedule_empty_channel_disconnect(member.guild.id)
