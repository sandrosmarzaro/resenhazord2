import discord
import structlog

from bot.adapters.discord.renderer import DiscordResponseRenderer
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandConfig
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.ports.discord_port import DiscordPort

logger = structlog.get_logger()


class DiscordInteractionHandler:
    COMMAND_PREFIX = ','

    def __init__(self, renderer: DiscordResponseRenderer | None = None) -> None:
        self._renderer = renderer or DiscordResponseRenderer()

    async def handle(self, port: DiscordPort, interaction: discord.Interaction, **kwargs) -> None:
        command_name = interaction.command.name if interaction.command else None
        if command_name is None:
            return

        text = self._build_command_text(command_name, kwargs)
        strategy = CommandRegistry.instance().get_strategy(text)

        if strategy is None:
            await port.send_message('Comando nao reconhecido.')
            return

        await port.defer()

        data = self._build_command_data(interaction, text)

        try:
            messages = await strategy.run(data)
        except BotError as e:
            await port.send_followup(e.user_message)
            return
        except Exception:
            logger.exception('discord_command_error', command=command_name)
            await port.send_followup('Ocorreu um erro ao executar o comando.')
            return

        if not messages:
            await port.send_followup('Sem resposta do bot.')
            return

        replies = self._renderer.render_many(messages)
        for reply in replies:
            await port.send_followup(reply.text, embed=reply.embed, file=reply.file)

    def _build_command_text(self, command_name: str, kwargs: dict) -> str:
        parts = [f'{self.COMMAND_PREFIX}{command_name}']
        strategy = CommandRegistry.instance().get_strategy(f'{self.COMMAND_PREFIX}{command_name}')
        if strategy is not None:
            parts.extend(self._extract_text_parts(strategy, kwargs))
        return ' '.join(parts)

    @staticmethod
    def _extract_text_parts(strategy: Command, kwargs: dict) -> list[str]:
        config: CommandConfig = strategy.config
        option_names = {opt.name for opt in config.options}
        flag_names = set(config.flags)
        parts: list[str] = []

        for opt in config.options:
            value = kwargs.get(opt.name)
            if value is not None:
                parts.append(str(value))

        for flag in config.flags:
            value = kwargs.get(flag)
            if value is True:
                parts.append(flag)

        if (
            'args' in kwargs
            and kwargs['args'] is not None
            and 'args' not in option_names
            and 'args' not in flag_names
        ):
            parts.append(str(kwargs['args']))

        return parts

    @staticmethod
    def _build_command_data(interaction: discord.Interaction, text: str) -> CommandData:
        return CommandData(
            text=text,
            jid=str(interaction.channel_id),
            sender_jid=str(interaction.user.id),
            message_id=str(interaction.id),
            is_group=interaction.guild_id is not None,
            push_name=interaction.user.display_name,
        )
