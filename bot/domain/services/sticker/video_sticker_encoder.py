import asyncio
import tempfile
from pathlib import Path
from typing import ClassVar


class VideoStickerEncoder:
    MAX_VIDEO_DURATION: ClassVar[int] = 10
    VIDEO_FPS: ClassVar[int] = 15

    @classmethod
    async def encode(cls, buffer: bytes, quality: int, working_size: int) -> bytes:
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
