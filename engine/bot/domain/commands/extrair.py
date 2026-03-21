import io

import structlog
from PIL import Image

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()


class ExtrairCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='extrair', category='download')

    @property
    def menu_description(self) -> str:
        return 'Extraia a imagem ou GIF original de um sticker.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if data.media_type != 'sticker' or data.media_source != 'quoted':
            return [Reply.to(data).text('Responda a um sticker para extrair a imagem! 🤦\u200d♂️')]

        logger.info(
            'extrair_command',
            jid=data.jid,
            is_animated=data.media_is_animated,
        )

        buffer = await self._whatsapp.download_media(data.message_id, data.media_source)

        try:
            if data.media_is_animated:
                gif_buffer = self._convert_to_gif(buffer)
                return [Reply.to(data).video_buffer(gif_buffer, gif_playback=True)]
            png_buffer = self._convert_to_png(buffer)
            return [Reply.to(data).image_buffer(png_buffer)]
        except Exception:
            logger.exception('extrair_conversion_error', jid=data.jid)
            return [Reply.to(data).text('Não consegui extrair a imagem do sticker 😅')]

    @staticmethod
    def _convert_to_png(buffer: bytes) -> bytes:
        img = Image.open(io.BytesIO(buffer))
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()

    @staticmethod
    def _convert_to_gif(buffer: bytes) -> bytes:
        img = Image.open(io.BytesIO(buffer))
        output = io.BytesIO()
        img.save(output, format='GIF', save_all=True)
        return output.getvalue()
