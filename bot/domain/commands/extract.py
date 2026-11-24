import io
from collections.abc import Iterator

import structlog
from PIL import Image, ImageSequence

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
                video = await StickerVideo.silent(frames)
                return [Reply.to(data).video_buffer(video, gif_playback=True)]
            return [Reply.to(data).image_buffer(frames)]
        except Exception:
            logger.exception('extrair_error', jid=data.jid)
            return [Reply.to(data).text('Não consegui extrair a imagem do sticker 😅')]

    @classmethod
    def _convert_to_png(cls, buffer: bytes) -> bytes:
        img = Image.open(io.BytesIO(buffer))
        output = io.BytesIO()
        img.crop(cls._content_box(img)).save(output, format='PNG')
        return output.getvalue()

    @classmethod
    def _convert_to_gif(cls, buffer: bytes) -> bytes:
        img = Image.open(io.BytesIO(buffer))
        box = cls._content_box(img)
        durations = MediaFormat.frame_durations(buffer, getattr(img, 'n_frames', 1))
        frames = cls._cropped_frames(img, box)
        output = io.BytesIO()
        next(frames).save(
            output, format='GIF', save_all=True, append_images=frames, duration=durations, loop=0
        )
        return output.getvalue()

    # A sticker pads a non-square picture with transparent borders, which a video can
    # only show as black bars: keep the box any frame paints. Frames are read one at a
    # time, since 150 RGBA frames held at once take ~150 MB.
    @staticmethod
    def _content_box(img: Image.Image) -> tuple[int, int, int, int] | None:
        boxes = [
            box
            for frame in ImageSequence.Iterator(img)
            if (box := frame.convert('RGBA').getchannel('A').getbbox())
        ]
        if not boxes:
            return None
        lefts, tops, rights, bottoms = zip(*boxes, strict=True)
        return min(lefts), min(tops), max(rights), max(bottoms)

    @staticmethod
    def _cropped_frames(
        img: Image.Image, box: tuple[int, int, int, int] | None
    ) -> Iterator[Image.Image]:
        for frame in ImageSequence.Iterator(img):
            yield frame.convert('RGBA').crop(box)
