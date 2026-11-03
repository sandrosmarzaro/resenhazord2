import asyncio
import io
import tempfile
from pathlib import Path

import anyio
from PIL import Image

from bot.data.sticker import STICKER_SIZE
from bot.domain.services.sticker.frame_shaper import FrameShaper
from bot.domain.services.sticker.media_format import MediaFormat


class StickerCreator:
    WEBP_QUALITY = 50
    MIN_WEBP_QUALITY = 1
    MIN_WORKING_SIZE = 16
    MAX_VIDEO_DURATION = 10
    VIDEO_FPS = 15
    DEFAULT_PACK = 'Resenha'
    DEFAULT_AUTHOR = 'Resenhazord2'
    MAX_FRAME_STRIDE = 4
    MAX_ANIMATED_STICKER_BYTES = 500_000

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
            return await cls._create_from_video(buffer, quality, working_size)
        # Pillow encoding is CPU-bound: off the event loop, the other in-flight commands
        # keep running.
        encode = (
            cls._create_from_animated_webp
            if MediaFormat.is_animated_webp(buffer)
            else cls._create_from_image
        )
        return await anyio.to_thread.run_sync(encode, buffer, sticker_type, quality, working_size)

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

    @classmethod
    def _create_from_animated_webp(
        cls, buffer: bytes, sticker_type: str, quality: int, working_size: int
    ) -> bytes:
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
        output = b''
        max_stride = min(cls.MAX_FRAME_STRIDE, max(1, n_frames // 2))
        for stride in range(1, max_stride + 1):
            output = cls._encode_animated_webp(all_frames, per_frame_ms, stride, quality)
            if len(output) <= cls.MAX_ANIMATED_STICKER_BYTES:
                return output
        return output

    @classmethod
    def _encode_animated_webp(
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

    @classmethod
    async def _create_from_video(cls, buffer: bytes, quality: int, working_size: int) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / 'input'
            output_path = Path(tmpdir) / 'output.webp'
            input_path.write_bytes(buffer)

            proc = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-i',
                str(input_path),
                '-vcodec',
                'libwebp',
                '-vf',
                (
                    f'scale={working_size}:{working_size}:'
                    'force_original_aspect_ratio=decrease:flags=bilinear,'
                    f'fps={cls.VIDEO_FPS},'
                    f'pad={working_size}:{working_size}:-1:-1:color=0x00000000,'
                    'scale=512:512:flags=neighbor'
                ),
                '-quality',
                str(quality),
                '-loop',
                '0',
                '-t',
                str(cls.MAX_VIDEO_DURATION),
                '-preset',
                'default',
                '-an',
                '-vsync',
                '0',
                str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                msg = f'ffmpeg failed: {stderr.decode().strip()}'
                raise RuntimeError(msg)

            return output_path.read_bytes()
