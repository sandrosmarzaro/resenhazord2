import discord
import structlog

from bot.application.command_registry import CommandRegistry
from bot.domain.models.command_data import CommandData
from bot.domain.models.contents.text_content import TextContent
from bot.ports.discord_port import DiscordPort

logger = structlog.get_logger()

COMMAND_PREFIX = ','


class DiscordInteractionHandler:
    async def handle(self, port: DiscordPort, interaction: discord.Interaction) -> None:
        command_name = interaction.command.name if interaction.command else None
        if command_name is None:
            return

        text = f'{COMMAND_PREFIX}{command_name}'
        strategy = CommandRegistry.instance().get_strategy(text)

        if strategy is None:
            await port.send_response('Comando não reconhecido. 🤷')
            return

        data = CommandData(
            text=text,
            jid=str(interaction.channel_id),
            sender_jid=str(interaction.user.id),
            message_id=str(interaction.id),
            is_group=interaction.guild_id is not None,
            push_name=interaction.user.display_name,
        )

        try:
            messages = await strategy.run(data)
        except Exception:
            logger.exception('discord_command_error', command=command_name)
            await port.send_response('Ocorreu um erro ao executar o comando. 😵')
            return

        if not messages:
            await port.send_response('Sem resposta do bot. 🤔')
            return

        content = messages[0].content
        if isinstance(content, TextContent):
            await port.send_response(content.text)
        else:
            await port.send_response(str(content))
