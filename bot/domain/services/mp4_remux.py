import asyncio
import tempfile
from pathlib import Path
from typing import ClassVar

import anyio

from bot.domain.exceptions import VideoRemuxError


class Mp4Remux:
    # WhatsApp shows "something is wrong with the video file" for some valid mp4s
    # (RedGifs: M4V brand, no edit list on a B-frame track, edts after mdia). Copying
    # the streams into a fresh ffmpeg mp4 fixes it without re-encoding.
    _TIMEOUT_SECONDS: ClassVar[float] = 60
    _TIMED_OUT: ClassVar[str] = 'ffmpeg timed out'
    _INPUT_ARGS: ClassVar[tuple[str, ...]] = (
        '-protocol_whitelist',
        'file',
        '-format_whitelist',
        'mov',
    )
    _REMUX_ARGS: ClassVar[tuple[str, ...]] = ('-c', 'copy', '-movflags', '+faststart')

    @classmethod
    async def remux(cls, video: bytes) -> bytes:
        # Files both ways: faststart seeks back to move the index to the front.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.mp4'
            target = Path(directory) / 'output.mp4'
            source.write_bytes(video)
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-v',
                'error',
                *cls._INPUT_ARGS,
                '-i',
                str(source),
                *cls._REMUX_ARGS,
                str(target),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                with anyio.fail_after(cls._TIMEOUT_SECONDS):
                    _, error = await process.communicate()
            except TimeoutError as timeout:
                process.kill()
                raise VideoRemuxError(cls._TIMED_OUT) from timeout
            if process.returncode != 0:
                raise VideoRemuxError(error.decode().strip())
            return target.read_bytes()
