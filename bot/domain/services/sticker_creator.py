import asyncio
import io
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


class StickerCreator:
    STICKER_SIZE = (512, 512)
    WEBP_QUALITY = 50
    MIN_WEBP_QUALITY = 1
    MIN_WORKING_SIZE = 16
    MAX_VIDEO_DURATION = 10
    VIDEO_FPS = 15
    DEFAULT_PACK = 'Resenha'
    DEFAULT_AUTHOR = 'Resenhazord2'
    MIN_VIDEO_SIGNATURE_LEN = 12

    @classmethod
    async def create(
        cls,
        buffer: bytes,
        sticker_type: str = 'full',
        quality_reduction: int = 0,
    ) -> bytes:
        quality = cls._effective_quality(quality_reduction)
        working_size = cls._effective_working_size(quality_reduction)
        if cls._is_video(buffer):
            return await cls._create_from_video(buffer, quality, working_size)
        return cls._create_from_image(buffer, sticker_type, quality, working_size)

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

        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality)
        return output.getvalue()

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

    @classmethod
    def _is_video(cls, buffer: bytes) -> bool:
        if len(buffer) < cls.MIN_VIDEO_SIGNATURE_LEN:
            return False
        # MP4/MOV: ftyp box at offset 4
        if buffer[4:8] == b'ftyp':
            return True
        # AVI
        if buffer[:4] == b'RIFF' and buffer[8:12] == b'AVI ':
            return True
        # MKV/WebM
        return buffer[:4] == b'\x1a\x45\xdf\xa3'
