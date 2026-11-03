import asyncio
import io
import tempfile
from pathlib import Path

import anyio
from PIL import Image, ImageDraw, ImageOps

from bot.domain.services.sticker.media_format import MediaFormat


class StickerCreator:
    STICKER_SIZE = (512, 512)
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
        reduced = round(cls.STICKER_SIZE[0] * (100 - quality_reduction) / 100)
        return max(cls.MIN_WORKING_SIZE, reduced)

    @classmethod
    def _create_from_image(
        cls, buffer: bytes, sticker_type: str, quality: int, working_size: int
    ) -> bytes:
        img = Image.open(io.BytesIO(buffer)).convert('RGBA')
        img = cls._transform_frame(img, sticker_type, working_size)
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
            all_frames.append(cls._transform_frame(src.convert('RGBA'), sticker_type, working_size))

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
    def _transform_frame(
        cls, img: Image.Image, sticker_type: str, working_size: int
    ) -> Image.Image:
        match sticker_type:
            case 'crop':
                img = ImageOps.fit(img, cls.STICKER_SIZE)
            case 'circle':
                img = cls._apply_circle_mask(img)
            case 'rounded':
                img = cls._apply_rounded_mask(img)
            case _:  # full
                img = cls._contain_on_transparent(img)
        if working_size < cls.STICKER_SIZE[0]:
            img = cls._pixelate(img, working_size)
        return img

    @classmethod
    def _pixelate(cls, img: Image.Image, working_size: int) -> Image.Image:
        small = img.resize((working_size, working_size), Image.Resampling.BILINEAR)
        return small.resize(cls.STICKER_SIZE, Image.Resampling.NEAREST)

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

    @classmethod
    def _contain_on_transparent(cls, img: Image.Image) -> Image.Image:
        img = ImageOps.contain(img, cls.STICKER_SIZE)
        canvas = Image.new('RGBA', cls.STICKER_SIZE, (0, 0, 0, 0))
        x = (cls.STICKER_SIZE[0] - img.width) // 2
        y = (cls.STICKER_SIZE[1] - img.height) // 2
        canvas.paste(img, (x, y), img)
        return canvas

    @classmethod
    def _apply_circle_mask(cls, img: Image.Image) -> Image.Image:
        img = ImageOps.fit(img, cls.STICKER_SIZE)
        mask = Image.new('L', cls.STICKER_SIZE, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, *cls.STICKER_SIZE), fill=255)
        canvas = Image.new('RGBA', cls.STICKER_SIZE, (0, 0, 0, 0))
        canvas.paste(img, mask=mask)
        return canvas

    @classmethod
    def _apply_rounded_mask(cls, img: Image.Image) -> Image.Image:
        img = ImageOps.fit(img, cls.STICKER_SIZE)
        radius = cls.STICKER_SIZE[0] // 8
        mask = Image.new('L', cls.STICKER_SIZE, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, *cls.STICKER_SIZE), radius=radius, fill=255)
        canvas = Image.new('RGBA', cls.STICKER_SIZE, (0, 0, 0, 0))
        canvas.paste(img, mask=mask)
        return canvas
