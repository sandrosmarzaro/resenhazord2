import io

from PIL import Image

from bot.data.sticker import MAX_ANIMATED_STICKER_BYTES, MAX_STICKER_QUALITY, STICKER_SIZE
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
        # Encoding a sticker that is already whole again only loses quality: the gateway
        # rewrites its pack and author either way.
        reusable = sticker_type == 'full' and not quality_reduction
        if reusable and await Work.cpu(cls._is_whole_sticker, buffer):
            return buffer
        working_size = cls._effective_working_size(quality_reduction)
        # Animations search the highest quality that fits; the reduction only lowers how
        # high they may go.
        max_quality = cls._effective_quality(quality_reduction, MAX_STICKER_QUALITY)
        if MediaFormat.is_video(buffer):
            return await VideoStickerEncoder.encode(buffer, sticker_type, max_quality, working_size)
        if MediaFormat.is_animated_webp(buffer):
            return await AnimatedWebpEncoder.encode(buffer, sticker_type, max_quality, working_size)
        quality = cls._effective_quality(quality_reduction)
        # Pillow encoding is CPU-bound: off the event loop, the other in-flight commands
        # keep running.
        return await Work.cpu(cls._create_from_image, buffer, sticker_type, quality, working_size)

    @staticmethod
    def _is_whole_sticker(buffer: bytes) -> bool:
        if MediaFormat.is_video(buffer) or len(buffer) > MAX_ANIMATED_STICKER_BYTES:
            return False
        image = Image.open(io.BytesIO(buffer))
        return image.format == 'WEBP' and image.size == STICKER_SIZE

    @classmethod
    def _effective_quality(cls, quality_reduction: int, quality: int = WEBP_QUALITY) -> int:
        reduced = round(quality * (100 - quality_reduction) / 100)
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
