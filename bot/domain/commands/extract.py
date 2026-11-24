import io

import structlog
from PIL import Image

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.sticker.media_format import MediaFormat
from bot.domain.services.sticker.sticker_video import StickerVideo
from bot.infrastructure.work import Work

logger = structlog.get_logger()


class ExtractCommand(Command):
    MUTE = 'mute'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='extrair',
            aliases=['extract'],
            flags=[Flag.SHOW, Flag.DM, self.MUTE],
            category=Category.DOWNLOAD,
        )

    @property
    def menu_description(self) -> str:
        return 'Extraia a imagem, GIF ou vídeo com áudio de um sticker. Use mute pra vir sem som.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if data.media_type != 'sticker' or data.media_source != 'quoted':
            return [Reply.to(data).text('Responda a um sticker pra eu extrair a imagem! 😊')]

        audio = None if self.MUTE in parsed.flags else data.media_audio
        logger.info('extrair_command', jid=data.jid, has_audio=audio is not None)

        try:
            buffer = await self._get_media(data)
            # Decided from the bytes: a reply from WhatsApp Web quotes the sticker
            # without its isAnimated flag.
            animated = MediaFormat.is_animated_webp(buffer)
            convert = self._convert_to_gif if animated else self._convert_to_png
            frames = await Work.cpu(convert, buffer)
            if audio:
                video = await StickerVideo.render(frames, audio, animated=animated)
                return [Reply.to(data).video_buffer(video)]
            if animated:
                return [Reply.to(data).video_buffer(frames, gif_playback=True)]
            return [Reply.to(data).image_buffer(frames)]
        except Exception:
            logger.exception('extrair_error', jid=data.jid)
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
