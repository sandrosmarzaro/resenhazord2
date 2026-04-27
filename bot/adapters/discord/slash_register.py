import inspect
import re
import unicodedata
from typing import Any, ClassVar, cast

import discord
import structlog
from discord import app_commands

from bot.adapters.discord.adapter import DiscordInteractionAdapter
from bot.adapters.discord.handler import DiscordInteractionHandler
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import ArgType, Command, CommandConfig, Flag, Platform

logger = structlog.get_logger()

SlashCallback = app_commands.Command


class DiscordSlashRegistrar:
    NAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'[^a-z0-9_-]')
    NAME_MAX_LENGTH: ClassVar[int] = 32
    DESC_MAX_LENGTH: ClassVar[int] = 100
    WHATSAPP_ONLY_FLAGS: ClassVar[frozenset[str]] = frozenset({Flag.DM, Flag.SHOW})

    def __init__(
        self,
        tree: app_commands.CommandTree,
        handler: DiscordInteractionHandler,
    ) -> None:
        self._tree = tree
        self._handler = handler

    def register_all(self) -> None:
        for command in CommandRegistry.instance().get_all():
            if not Platform.supports(command.config.platforms, Platform.DISCORD):
                continue
            self._register(command)
            for alias in command.config.aliases:
                self._register_alias(command, alias)
            logger.info('discord_command_registered', name=command.config.name)

    def _register(self, command: Command) -> None:
        config = command.config
        discord_name = self._normalize_name(config.name)
        self._handler.register_name(discord_name, f',{config.name}')
        self._add_to_tree(discord_name, command)

    def _register_alias(self, command: Command, alias: str) -> None:
        discord_name = self._normalize_name(alias)
        self._handler.register_name(discord_name, f',{alias}')
        self._add_to_tree(discord_name, command)

    def _add_to_tree(self, discord_name: str, command: Command) -> None:
        if self._tree.get_command(discord_name):
            logger.debug('command_already_registered', name=discord_name)
            return

        slash_cmd = self._build_slash_command(discord_name, command)
        self._configure_options(slash_cmd, command.config)
        self._tree.add_command(slash_cmd)

    def _build_slash_command(self, discord_name: str, command: Command) -> app_commands.Command:
        config = command.config
        description = command.menu_description[: self.DESC_MAX_LENGTH]
        callback = self._make_callback()
        cast('Any', callback).__signature__ = self._build_signature(config)
        return app_commands.Command(
            name=discord_name,
            description=description,
            callback=cast('Any', callback),
        )

    def _configure_options(self, slash_cmd: app_commands.Command, config: CommandConfig) -> None:
        params = slash_cmd._params
        for opt in config.options:
            if opt.name not in params:
                continue
            if opt.values:
                params[opt.name].choices = [
                    app_commands.Choice(name=v, value=v) for v in opt.values
                ]
            if opt.description:
                params[opt.name].description = opt.description

        if 'args' in params and config.args_label:
            params['args'].description = config.args_label

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
        params.extend(cls._option_parameters(config))
        params.extend(cls._flag_parameters(config))
        args_param = cls._args_parameter(config)
        if args_param is not None:
            params.append(args_param)
        return inspect.Signature(params)

    @staticmethod
    def _option_parameters(config: CommandConfig) -> list[inspect.Parameter]:
        return [
            inspect.Parameter(
                opt.name,
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=str | None,
            )
            for opt in config.options
            if opt.values or opt.pattern
        ]

    @classmethod
    def _flag_parameters(cls, config: CommandConfig) -> list[inspect.Parameter]:
        return [
            inspect.Parameter(
                flag,
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=bool | None,
            )
            for flag in config.flags
            if flag not in cls.WHATSAPP_ONLY_FLAGS
        ]

    @staticmethod
    def _args_parameter(config: CommandConfig) -> inspect.Parameter | None:
        if config.args == ArgType.NONE:
            return None
        default = inspect.Parameter.empty if config.args == ArgType.REQUIRED else None
        annotation = str if config.args == ArgType.REQUIRED else (str | None)
        return inspect.Parameter(
            'args',
            inspect.Parameter.KEYWORD_ONLY,
            default=default,
            annotation=annotation,
        )

    @classmethod
    def _normalize_name(cls, name: str) -> str:
        normalized = unicodedata.normalize('NFD', name.lower())
        ascii_only = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        cleaned = cls.NAME_PATTERN.sub('', ascii_only.replace(' ', '-'))
        return cleaned[: cls.NAME_MAX_LENGTH]
