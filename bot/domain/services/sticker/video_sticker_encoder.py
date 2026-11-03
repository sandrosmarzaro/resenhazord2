import asyncio
import math
import tempfile
from pathlib import Path
from typing import ClassVar

from bot.data.sticker import (
    COVER_STICKER_TYPES,
    MAX_ANIMATED_STICKER_BYTES,
    MAX_FRAME_STRIDE,
    VIDEO_ALPHA_MASKS,
)
from bot.domain.exceptions import StickerTooLargeError


class VideoStickerEncoder:
    MAX_VIDEO_DURATION: ClassVar[int] = 10
    VIDEO_FPS: ClassVar[int] = 15

    @classmethod
    async def encode(
        cls, buffer: bytes, sticker_type: str, quality: int, working_size: int
    ) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / 'input'
            input_path.write_bytes(buffer)
            # Like the animated webp path: drop frames only as a last resort, when the
            # sticker is over the limit at full frame rate.
            stride = 1
            while stride <= MAX_FRAME_STRIDE:
                output_path = Path(tmpdir) / f'output-{stride}.webp'
                graph = cls._filter_graph(sticker_type, working_size, stride)
                await cls._run_ffmpeg(input_path, output_path, graph, quality)
                output = output_path.read_bytes()
                if len(output) <= MAX_ANIMATED_STICKER_BYTES:
                    return output
                # Real footage shrinks about in proportion to the frames kept, so skip
                # the strides that can't fit instead of paying an ffmpeg run for each.
                stride = max(stride + 1, math.ceil(len(output) / MAX_ANIMATED_STICKER_BYTES))
        raise StickerTooLargeError

    @classmethod
    async def _run_ffmpeg(
        cls, input_path: Path, output_path: Path, filter_graph: str, quality: int
    ) -> None:
        proc = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-i',
            str(input_path),
            '-vcodec',
            'libwebp',
            '-vf',
            filter_graph,
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

    @classmethod
    def _filter_graph(cls, sticker_type: str, working_size: int, stride: int) -> str:
        size = f'{working_size}:{working_size}'
        fps = f'fps={cls.VIDEO_FPS}/{stride}'
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
