import asyncio
import json
import tempfile
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import ClassVar

from bot.data.sticker import COVER_STICKER_TYPES, VIDEO_ALPHA_MASKS
from bot.domain.services.sticker.frame_rate_ladder import EncodePlan, FrameRateLadder
from bot.domain.services.sticker.video_clip import VideoClip


class VideoStickerEncoder:
    MAX_VIDEO_DURATION: ClassVar[int] = 10
    # Frames spread over the clip that a sticker's size is measured on: libwebp encodes
    # each frame whole, so 20 of them predict the full encode within about 1%.
    SAMPLE_FRAMES: ClassVar[int] = 20
    # Any member can hand over the video: a crafted one can be an hls or concat
    # playlist that makes ffmpeg fetch URLs or read local files.
    INPUT_ARGS: ClassVar[tuple[str, ...]] = (
        '-protocol_whitelist',
        'file',
        '-format_whitelist',
        'mov,avi,matroska',
    )
    _PROBE_ARGS: ClassVar[tuple[str, ...]] = (
        '-select_streams',
        'v:0',
        '-show_entries',
        'stream=avg_frame_rate:format=duration',
        '-of',
        'json',
    )
    _WEBP_ARGS: ClassVar[tuple[str, ...]] = ('-preset', 'default', '-an', '-vsync', '0')

    @classmethod
    async def encode(
        cls, buffer: bytes, sticker_type: str, max_quality: int, working_size: int
    ) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'input'
            source.write_bytes(buffer)
            clip = await cls._probe(source)
            graph = partial(cls._filter_graph, sticker_type, working_size)
            sample = await cls._sample(source, graph(cls.SAMPLE_FRAMES / clip.seconds))
            ladder = FrameRateLadder(clip, partial(cls._frame_bytes, sample))
            return await ladder.fit(max_quality, partial(cls._encode_clip, source, graph))

    @classmethod
    async def _probe(cls, source: Path) -> VideoClip:
        stdout = await cls._run(
            'ffprobe', '-v', 'error', *cls.INPUT_ARGS, '-i', str(source), *cls._PROBE_ARGS
        )
        return VideoClip.from_probe(json.loads(stdout), cls.MAX_VIDEO_DURATION)

    # Shaped once into a lossless file, so each quality the ladder tries encodes only
    # the sample instead of decoding the whole video again.
    @classmethod
    async def _sample(cls, source: Path, filter_graph: str) -> Path:
        sample = source.with_name('sample.mkv')
        await cls._run(
            'ffmpeg',
            *cls._read(source),
            '-vf',
            filter_graph,
            '-frames:v',
            str(cls.SAMPLE_FRAMES),
            '-an',
            '-c:v',
            'ffv1',
            str(sample),
        )
        return sample

    @classmethod
    async def _frame_bytes(cls, sample: Path, quality: int) -> int:
        output = sample.with_name(f'sample-{quality}.webp')
        await cls._run(
            'ffmpeg',
            '-i',
            str(sample),
            '-vcodec',
            'libwebp',
            '-quality',
            str(quality),
            *cls._WEBP_ARGS,
            str(output),
        )
        return len(output.read_bytes()) // cls.SAMPLE_FRAMES

    @classmethod
    async def _encode_clip(
        cls, source: Path, filter_graph: Callable[[float], str], plan: EncodePlan
    ) -> bytes:
        output = source.with_name('output.webp')
        await cls._run(
            'ffmpeg',
            *cls._read(source),
            '-vcodec',
            'libwebp',
            '-vf',
            filter_graph(plan.fps),
            '-quality',
            str(plan.quality),
            '-loop',
            '0',
            '-t',
            str(cls.MAX_VIDEO_DURATION),
            *cls._WEBP_ARGS,
            str(output),
        )
        return output.read_bytes()

    @classmethod
    def _read(cls, source: Path) -> tuple[str, ...]:
        return (*cls.INPUT_ARGS, '-i', str(source))

    @staticmethod
    async def _run(program: str, *args: str) -> bytes:
        proc = await asyncio.create_subprocess_exec(
            program,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            msg = f'{program} failed: {stderr.decode().strip()}'
            raise RuntimeError(msg)
        return stdout

    @classmethod
    def _filter_graph(cls, sticker_type: str, working_size: int, fps: float) -> str:
        size = f'{working_size}:{working_size}'
        frame_rate = f'fps={fps:g}'
        # Without an alpha channel the transparent pad and the masks come out black.
        if sticker_type in COVER_STICKER_TYPES:
            fit = (
                f'scale={size}:force_original_aspect_ratio=increase:flags=bilinear,'
                f'{frame_rate},crop={size}'
            )
        else:
            fit = (
                f'scale={size}:force_original_aspect_ratio=decrease:flags=bilinear,'
                f'{frame_rate},pad={size}:-1:-1:color=0x00000000'
            )
        mask = VIDEO_ALPHA_MASKS.get(sticker_type)
        shape = f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{mask}'" if mask else ''
        return f'format=rgba,{fit}{shape},scale=512:512:flags=neighbor'
