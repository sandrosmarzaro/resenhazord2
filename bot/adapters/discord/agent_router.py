from dataclasses import replace
from typing import Any, ClassVar

import discord
import structlog

from bot.adapters.discord.renderer import DiscordReply, DiscordResponseRenderer
from bot.application.agent_executor import AgentExecutor
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Platform
from bot.domain.models.command_data import CommandData

logger = structlog.get_logger()


class DiscordAgentRouter:
    UNKNOWN_COMMAND: ClassVar[str] = 'Comando não reconhecido.'
    EMPTY_REPLY: ClassVar[str] = 'Sem resposta do comando.'
    GENERIC_ERROR: ClassVar[str] = 'Erro ao processar comando.'
    EMPTY_TEXT_PLACEHOLDER: ClassVar[str] = '\u200b'

    def __init__(self, renderer: DiscordResponseRenderer | None = None) -> None:
        self._renderer = renderer or DiscordResponseRenderer()

    async def handle_dm(self, message: discord.Message) -> None:
        await self._dispatch(message, self._dm_data(message))

    async def handle_mention(self, message: discord.Message) -> None:
        logger.info('discord_agent_mention', text=message.content)
        await self._dispatch(message, self._group_data(message))

    async def _dispatch(self, message: discord.Message, data: CommandData) -> None:
        try:
            await self._run_pipeline(message, data)
        except Exception:
            logger.exception('discord_agent_error', dm=not data.is_group)
            await message.reply(self.GENERIC_ERROR)

    async def _run_pipeline(self, message: discord.Message, data: CommandData) -> None:
        executor = AgentExecutor(CommandRegistry.instance())
        result = await executor.run(data)

        strategy = CommandRegistry.instance().get_strategy(result.text)
        if strategy is None:
            await message.reply(self.UNKNOWN_COMMAND)
            return

        command_data = replace(data, text=result.text)
        messages = await strategy.run(command_data)

        if not messages:
            await message.reply(self.EMPTY_REPLY)
            return

        for outbound in messages:
            reply = await self._renderer.render_async(outbound)
            await self._send_reply(message, reply)

    async def _send_reply(self, message: discord.Message, reply: DiscordReply) -> None:
        kwargs: dict[str, Any] = {}
        if reply.file is not None:
            kwargs['file'] = reply.file
        if reply.embed is not None:
            kwargs['embed'] = reply.embed
        await message.reply(reply.text or self.EMPTY_TEXT_PLACEHOLDER, **kwargs)

    @staticmethod
    def _dm_data(message: discord.Message) -> CommandData:
        return CommandData(
            text=message.content,
            jid=str(message.channel.id),
            sender_jid=str(message.author.id),
            is_group=False,
            platform=Platform.DISCORD,
        )

    @staticmethod
    def _group_data(message: discord.Message) -> CommandData:
        return CommandData(
            text=message.content,
            jid=str(message.channel.id),
            sender_jid=str(message.author.id),
            is_group=True,
            platform=Platform.DISCORD,
        )
