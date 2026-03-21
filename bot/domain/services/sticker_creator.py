"""Create WhatsApp stickers from images and videos using Pillow + ffmpeg."""

import asyncio
import io
import struct
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

STICKER_SIZE = (512, 512)
WEBP_QUALITY = 50
MAX_VIDEO_DURATION = 10
VIDEO_FPS = 15
PACK_NAME = 'Resenhazord2'
PACK_AUTHOR = 'Resenha'
MIN_VIDEO_SIGNATURE_LEN = 12


class StickerCreator:
    """Convert images and videos into WhatsApp-compatible WebP stickers."""

    @classmethod
    async def create(cls, buffer: bytes, sticker_type: str = 'full') -> bytes:
        """Create a sticker from an image or video buffer.

        Args:
            buffer: Raw image or video bytes.
            sticker_type: One of 'full', 'crop', 'circle', 'rounded'.

        Returns:
            WebP sticker bytes with EXIF metadata.
        """
        if cls._is_video(buffer):
            return await cls._create_from_video(buffer)
        return cls._create_from_image(buffer, sticker_type)

    @classmethod
    def _create_from_image(cls, buffer: bytes, sticker_type: str) -> bytes:
        img = Image.open(io.BytesIO(buffer)).convert('RGBA')

        match sticker_type:
            case 'crop':
                img = ImageOps.fit(img, STICKER_SIZE)
            case 'circle':
                img = cls._apply_circle_mask(img)
            case 'rounded':
                img = cls._apply_rounded_mask(img)
            case _:  # full
                img = cls._contain_on_transparent(img)

        output = io.BytesIO()
        img.save(output, format='WEBP', quality=WEBP_QUALITY)
        return cls._inject_exif(output.getvalue())

    @classmethod
    async def _create_from_video(cls, buffer: bytes) -> bytes:
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
                    f'fps={VIDEO_FPS},'
                    'pad=512:512:-1:-1:color=0x00000000'
                ),
                '-loop',
                '0',
                '-t',
                str(MAX_VIDEO_DURATION),
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

            return cls._inject_exif(output_path.read_bytes())

    @classmethod
    def _contain_on_transparent(cls, img: Image.Image) -> Image.Image:
        """Resize to fit within 512x512 and center on transparent canvas."""
        img = ImageOps.contain(img, STICKER_SIZE)
        canvas = Image.new('RGBA', STICKER_SIZE, (0, 0, 0, 0))
        x = (STICKER_SIZE[0] - img.width) // 2
        y = (STICKER_SIZE[1] - img.height) // 2
        canvas.paste(img, (x, y), img)
        return canvas

    @classmethod
    def _apply_circle_mask(cls, img: Image.Image) -> Image.Image:
        """Crop to square, resize to 512x512, apply circular mask."""
        img = ImageOps.fit(img, STICKER_SIZE)
        mask = Image.new('L', STICKER_SIZE, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, *STICKER_SIZE), fill=255)
        canvas = Image.new('RGBA', STICKER_SIZE, (0, 0, 0, 0))
        canvas.paste(img, mask=mask)
        return canvas

    @classmethod
    def _apply_rounded_mask(cls, img: Image.Image) -> Image.Image:
        """Crop to square, resize to 512x512, apply rounded corners."""
        img = ImageOps.fit(img, STICKER_SIZE)
        radius = STICKER_SIZE[0] // 8
        mask = Image.new('L', STICKER_SIZE, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, *STICKER_SIZE), radius=radius, fill=255)
        canvas = Image.new('RGBA', STICKER_SIZE, (0, 0, 0, 0))
        canvas.paste(img, mask=mask)
        return canvas

    @staticmethod
    def _is_video(buffer: bytes) -> bool:
        """Detect video by checking common file signatures."""
        if len(buffer) < MIN_VIDEO_SIGNATURE_LEN:
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
    def _build_exif(cls) -> bytes:
        """Build EXIF bytes with WhatsApp sticker pack metadata.

        Uses custom EXIF tags 0x4501 (pack name) and 0x4502 (author)
        in a standard TIFF/IFD structure (little-endian).
        """
        pack_bytes = PACK_NAME.encode('utf-8') + b'\x00'
        author_bytes = PACK_AUTHOR.encode('utf-8') + b'\x00'

        num_entries = 2
        # IFD: 2 bytes count + entries * 12 bytes + 4 bytes next offset
        ifd_size = 2 + num_entries * 12 + 4
        data_start = 8 + ifd_size  # 8 bytes TIFF header

        # Entry format: tag(2) + type(2) + count(4) + value_or_offset(4)
        # Type 2 = ASCII
        entry1 = struct.pack('<HHII', 0x4501, 2, len(pack_bytes), data_start)
        entry2 = struct.pack('<HHII', 0x4502, 2, len(author_bytes), data_start + len(pack_bytes))

        # TIFF header (little-endian)
        header = b'\x49\x49\x2a\x00\x08\x00\x00\x00'
        ifd = struct.pack('<H', num_entries) + entry1 + entry2 + b'\x00\x00\x00\x00'

        return header + ifd + pack_bytes + author_bytes

    @classmethod
    def _inject_exif(cls, webp_data: bytes) -> bytes:
        """Inject EXIF metadata into a WebP file's RIFF structure."""
        exif_payload = cls._build_exif()
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
