import asyncio
import io
import struct
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


class StickerCreator:
    STICKER_SIZE = (512, 512)
    WEBP_QUALITY = 50
    MAX_VIDEO_DURATION = 10
    VIDEO_FPS = 15
    DEFAULT_PACK = 'Resenha'
    DEFAULT_AUTHOR = 'Resenhazord2'
    MIN_VIDEO_SIGNATURE_LEN = 12
    EXIF_TAG_PACK = 0x4501
    EXIF_TAG_AUTHOR = 0x4502

    @classmethod
    async def create(
        cls,
        buffer: bytes,
        sticker_type: str = 'full',
        pack: str = '',
        author: str = '',
    ) -> bytes:
        pack = pack or cls.DEFAULT_PACK
        author = author or cls.DEFAULT_AUTHOR
        if cls._is_video(buffer):
            return await cls._create_from_video(buffer, pack, author)
        return cls._create_from_image(buffer, sticker_type, pack, author)

    @classmethod
    def _build_exif_bytes(cls, pack: str, author: str) -> bytes:
        exif = Image.Exif()
        exif[cls.EXIF_TAG_PACK] = pack
        exif[cls.EXIF_TAG_AUTHOR] = author
        return exif.tobytes()

    @classmethod
    def _create_from_image(cls, buffer: bytes, sticker_type: str, pack: str, author: str) -> bytes:
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

        output = io.BytesIO()
        img.save(
            output,
            format='WEBP',
            quality=cls.WEBP_QUALITY,
            exif=cls._build_exif_bytes(pack, author),
        )
        return output.getvalue()

    @classmethod
    async def _create_from_video(cls, buffer: bytes, pack: str, author: str) -> bytes:
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
                    'scale=512:512:force_original_aspect_ratio=decrease,'
                    f'fps={cls.VIDEO_FPS},'
                    'pad=512:512:-1:-1:color=0x00000000'
                ),
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

            return cls._inject_exif(output_path.read_bytes(), pack, author)

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

    @classmethod
    def _inject_exif(cls, webp_data: bytes, pack: str, author: str) -> bytes:
        exif_payload = cls._build_exif_bytes(pack, author)
        # EXIF chunk: 'EXIF' + size (little-endian u32) + data
        exif_chunk = b'EXIF' + struct.pack('<I', len(exif_payload)) + exif_payload
        # Pad to even length (RIFF requirement)
        if len(exif_payload) % 2 != 0:
            exif_chunk += b'\x00'

        # Check if this is an extended WebP (VP8X) or simple
        fourcc = webp_data[12:16]
        if fourcc == b'VP8X':
            # Set EXIF flag (bit 3) in VP8X flags byte
            flags = webp_data[20]
            flags |= 0x08  # Set Exif metadata present flag
            result = webp_data[:20] + bytes([flags]) + webp_data[21:] + exif_chunk
        else:
            # Simple WebP (VP8 or VP8L) — wrap in VP8X container
            width = Image.open(io.BytesIO(webp_data)).size[0] - 1
            height = Image.open(io.BytesIO(webp_data)).size[1] - 1
            # VP8X: flags(4) + width-1(3 bytes LE) + height-1(3 bytes LE) = 10 bytes
            vp8x_flags = 0x08  # EXIF present
            vp8x_data = struct.pack('<I', vp8x_flags)
            vp8x_data += struct.pack('<I', width)[:3]
            vp8x_data += struct.pack('<I', height)[:3]
            vp8x_chunk = b'VP8X' + struct.pack('<I', 10) + vp8x_data
            # Rebuild: RIFF header + WEBP + VP8X + original payload + EXIF
            original_payload = webp_data[12:]  # After 'RIFF' + size + 'WEBP'
            result = b'RIFF\x00\x00\x00\x00WEBP' + vp8x_chunk
            result += original_payload + exif_chunk

        # Update RIFF size (total file size - 8)
        riff_size = len(result) - 8
        return result[:4] + struct.pack('<I', riff_size) + result[8:]
