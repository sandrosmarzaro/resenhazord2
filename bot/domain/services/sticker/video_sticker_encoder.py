import asyncio
import tempfile
from pathlib import Path
from typing import ClassVar

from bot.data.sticker import COVER_STICKER_TYPES, VIDEO_ALPHA_MASKS


class VideoStickerEncoder:
    MAX_VIDEO_DURATION: ClassVar[int] = 10
    VIDEO_FPS: ClassVar[int] = 15

    @classmethod
    async def encode(
        cls, buffer: bytes, sticker_type: str, quality: int, working_size: int
    ) -> bytes:
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
                cls._filter_graph(sticker_type, working_size),
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
    def _filter_graph(cls, sticker_type: str, working_size: int) -> str:
        size = f'{working_size}:{working_size}'
        fps = f'fps={cls.VIDEO_FPS}'
        # Without an alpha channel the transparent pad and the masks come out black.
        if sticker_type in COVER_STICKER_TYPES:
            fit = (
                f'scale={size}:force_original_aspect_ratio=increase:flags=bilinear,{fps},'
                f'crop={size}'
            )
        else:
            fit = (
                f'scale={size}:force_original_aspect_ratio=decrease:flags=bilinear,{fps},'
                f'pad={size}:-1:-1:color=0x00000000'
            )
        mask = VIDEO_ALPHA_MASKS.get(sticker_type)
        shape = f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{mask}'" if mask else ''
        return f'format=rgba,{fit}{shape},scale=512:512:flags=neighbor'
