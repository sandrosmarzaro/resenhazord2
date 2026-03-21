import time

import structlog

from bot.data.drive import EXTENSIONS, TYPE_LABELS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.discord import DiscordService

logger = structlog.get_logger()


class DriveCommand(Command):
    SUPPORTED_MEDIA = frozenset(('image', 'video', 'audio'))
    MIN_PARTS = 2

    def __init__(self, discord: DiscordService | None = None) -> None:
        super().__init__()
        self._discord = discord

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='drive',
            flags=['new'],
            args=ArgType.REQUIRED,
            group_only=True,
            category='grupo',
        )

    @property
    def menu_description(self) -> str:
        return 'Arquiva uma mídia no Discord. Use: ,drive <categoria> <canal>'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        parts = parsed.rest.strip().split()
        if len(parts) < self.MIN_PARTS:
            return [Reply.to(data).text('Uso: ,drive <categoria> <canal>')]

        category = parts[0]
        channel = ' '.join(parts[1:])
        is_new = 'new' in parsed.flags

        if not data.has_media or data.media_type not in self.SUPPORTED_MEDIA:
            return [
                Reply.to(data).text(
                    'Nenhuma mídia encontrada. Envie ou marque uma imagem, vídeo ou áudio.'
                )
            ]

        if not self._discord:
            return [Reply.to(data).text('Discord não configurado.')]

        logger.info(
            'drive_command',
            jid=data.jid,
            category=category,
            channel=channel,
            is_new=is_new,
            media_type=data.media_type,
        )

        try:
            return await self._execute_upload(data, category, channel, is_new=is_new)
        except Exception:
            logger.exception('drive_error', category=category, channel=channel)
            return [Reply.to(data).text('Erro ao salvar no Drive 📁')]

    async def _execute_upload(
        self,
        data: CommandData,
        category: str,
        channel: str,
        *,
        is_new: bool,
    ) -> list[BotMessage]:
        channels = await self._discord.get_channels()

        category_channel = self._discord.find_category(channels, category)
        if not category_channel:
            if not is_new:
                return [
                    Reply.to(data).text(
                        f'Categoria *{category}* não encontrada. Use a flag `new` para criar.'
                    )
                ]
            category_channel = await self._discord.create_category(category)

        target_channel = self._discord.find_channel(channels, channel, category_channel['id'])
        if not target_channel:
            if not is_new:
                return [
                    Reply.to(data).text(
                        f'Canal *{channel}* não encontrado em *{category}*.'
                        ' Use a flag `new` para criar.'
                    )
                ]
            target_channel = await self._discord.create_channel(channel, category_channel['id'])

        buffer = await self._whatsapp.download_media(data.message_id, data.media_source)

        ext = EXTENSIONS[data.media_type]
        label = TYPE_LABELS[data.media_type]
        timestamp = int(time.time() * 1000)
        filename = f'{label}_{timestamp}.{ext}'

        await self._discord.upload_media(target_channel['id'], buffer, filename)

        return [Reply.to(data).text(f'✅ Mídia salva em *{category}* > *#{channel}*')]
