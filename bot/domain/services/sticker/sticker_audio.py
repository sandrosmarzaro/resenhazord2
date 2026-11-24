import asyncio
import tempfile
from pathlib import Path
from typing import ClassVar

import anyio

from bot.domain.exceptions import StickerAudioError
from bot.domain.services.sticker.video_sticker_encoder import VideoStickerEncoder


class StickerAudio:
    # A video's soundtrack, cut like its sticker, as the ogg/opus WhatsApp's own audio
    # stickers carry.
    _TIMEOUT_SECONDS: ClassVar[float] = 60
    _TIMED_OUT: ClassVar[str] = 'ffmpeg timed out'
    _PROBE_ARGS: ClassVar[tuple[str, ...]] = (
        '-select_streams',
        'a:0',
        '-show_entries',
        'stream=index',
        '-of',
        'csv=p=0',
    )
    _ENCODE_ARGS: ClassVar[tuple[str, ...]] = (
        '-map',
        '0:a:0',
        '-t',
        str(VideoStickerEncoder.MAX_VIDEO_DURATION),
        '-ac',
        '1',
        '-ar',
        '48000',
        '-c:a',
        'libopus',
        '-b:a',
        '64k',
        # A phone's AAC track starts with priming samples that ffmpeg carries into the
        # ogg as negative timestamps, and Android won't play the sticker's sound then.
        '-avoid_negative_ts',
        'make_zero',
        '-f',
        'ogg',
        'pipe:1',
    )

    @classmethod
    async def from_video(cls, video: bytes) -> bytes | None:
        # A file, not stdin: an mp4 keeps its index at the end, which a pipe can't seek to.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input'
            source.write_bytes(video)
            probed = await cls._run(
                'ffprobe', *VideoStickerEncoder.INPUT_ARGS, '-i', str(source), *cls._PROBE_ARGS
            )
            if not probed.strip():
                return None
            return await cls._run(
                'ffmpeg', *VideoStickerEncoder.INPUT_ARGS, '-i', str(source), *cls._ENCODE_ARGS
            )

    @classmethod
    async def _run(cls, *args: str) -> bytes:
        process = await asyncio.create_subprocess_exec(
            args[0],
            '-v',
            'error',
            *args[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            with anyio.fail_after(cls._TIMEOUT_SECONDS):
                output, error = await process.communicate()
        except TimeoutError as timeout:
            process.kill()
            raise StickerAudioError(cls._TIMED_OUT) from timeout
        if process.returncode != 0:
            raise StickerAudioError(error.decode().strip())
        return output
