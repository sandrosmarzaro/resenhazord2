import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()


class ScarraCommand(Command):
    SUPPORTED_MEDIA = frozenset(('image', 'video', 'audio'))
    DEFAULT_CAPTION = 'Escarrado! 😝'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='scarra', group_only=True, category='download')

    @property
    def menu_description(self) -> str:
        return 'Baixe a mídia de visualização única marcada.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if data.media_source != 'view_once' or data.media_type not in self.SUPPORTED_MEDIA:
            return [
                Reply.to(data).text(
                    'Burro burro! Você precisa marcar uma mensagem única pra eu escarrar! 🤦\u200d♂️'
                )
            ]

        logger.info(
            'scarra_command',
            jid=data.jid,
            media_type=data.media_type,
        )

        buffer = await self._whatsapp.download_media(data.message_id, data.media_source)
        caption = data.media_caption or self.DEFAULT_CAPTION

        if data.media_type == 'image':
            return [Reply.to(data).image_buffer(buffer, caption)]
        if data.media_type == 'video':
            return [Reply.to(data).video_buffer(buffer, caption)]
        return [Reply.to(data).audio_buffer(buffer)]
