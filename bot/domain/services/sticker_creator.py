import io

from PIL import Image

from bot.data.sticker import STICKER_SIZE
from bot.domain.services.sticker.animated_webp_encoder import AnimatedWebpEncoder
from bot.domain.services.sticker.frame_shaper import FrameShaper
from bot.domain.services.sticker.media_format import MediaFormat
from bot.domain.services.sticker.video_sticker_encoder import VideoStickerEncoder
from bot.infrastructure.work import Work


class StickerCreator:
    WEBP_QUALITY = 50
    MIN_WEBP_QUALITY = 1
    MIN_WORKING_SIZE = 16
    DEFAULT_PACK = 'Resenha'
    DEFAULT_AUTHOR = 'Resenhazord2'

    @classmethod
    async def create(
        cls,
        buffer: bytes,
        sticker_type: str = 'full',
        quality_reduction: int = 0,
    ) -> bytes:
        quality = cls._effective_quality(quality_reduction)
        working_size = cls._effective_working_size(quality_reduction)
        if MediaFormat.is_video(buffer):
            return await VideoStickerEncoder.encode(buffer, sticker_type, quality, working_size)
        # Pillow encoding is CPU-bound: off the event loop, the other in-flight commands
        # keep running.
        encode = (
            AnimatedWebpEncoder.encode
            if MediaFormat.is_animated_webp(buffer)
            else cls._create_from_image
        )
        return await Work.cpu(encode, buffer, sticker_type, quality, working_size)

    @classmethod
    def _effective_quality(cls, quality_reduction: int) -> int:
        reduced = round(cls.WEBP_QUALITY * (100 - quality_reduction) / 100)
        return max(cls.MIN_WEBP_QUALITY, reduced)

    @classmethod
    def _effective_working_size(cls, quality_reduction: int) -> int:
        reduced = round(STICKER_SIZE[0] * (100 - quality_reduction) / 100)
        return max(cls.MIN_WORKING_SIZE, reduced)

    @classmethod
    def _create_from_image(
        cls, buffer: bytes, sticker_type: str, quality: int, working_size: int
    ) -> bytes:
        img = Image.open(io.BytesIO(buffer)).convert('RGBA')
        img = FrameShaper.shape(img, sticker_type, working_size)
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality)
        return output.getvalue()
