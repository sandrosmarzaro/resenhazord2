import io

from PIL import Image

from bot.data.sticker import MAX_ANIMATED_STICKER_BYTES, MAX_FRAME_STRIDE
from bot.domain.exceptions import StickerTooLargeError
from bot.domain.services.sticker.frame_shaper import FrameShaper
from bot.domain.services.sticker.media_format import MediaFormat


class AnimatedWebpEncoder:
    @classmethod
    def encode(cls, buffer: bytes, sticker_type: str, quality: int, working_size: int) -> bytes:
        src = Image.open(io.BytesIO(buffer))
        n_frames = getattr(src, 'n_frames', 1)
        per_frame_ms = MediaFormat.frame_durations(buffer, n_frames)

        all_frames: list[Image.Image] = []
        for i in range(n_frames):
            src.seek(i)
            all_frames.append(FrameShaper.shape(src.convert('RGBA'), sticker_type, working_size))

        # Reduction degrades quality + pixelation; only drop frames as a last
        # resort when pixelation breaks inter-frame compression and the file
        # exceeds the animated-sticker limit.
        max_stride = min(MAX_FRAME_STRIDE, max(1, n_frames // 2))
        for stride in range(1, max_stride + 1):
            output = cls._encode(all_frames, per_frame_ms, stride, quality)
            if len(output) <= MAX_ANIMATED_STICKER_BYTES:
                return output
        raise StickerTooLargeError

    @classmethod
    def _encode(
        cls,
        all_frames: list[Image.Image],
        per_frame_ms: list[int],
        stride: int,
        quality: int,
    ) -> bytes:
        frames = all_frames[::stride]
        durations = [sum(per_frame_ms[i : i + stride]) for i in range(0, len(all_frames), stride)]
        output = io.BytesIO()
        frames[0].save(
            output,
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            quality=quality,
        )
        return output.getvalue()
