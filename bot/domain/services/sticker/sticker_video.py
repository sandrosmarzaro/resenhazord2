import asyncio
import tempfile
from pathlib import Path
from typing import ClassVar

import anyio

from bot.domain.exceptions import StickerVideoError


class StickerVideo:
    # An audio sticker plays its animation in a loop for as long as its audio lasts.
    # Rebuild that as an mp4 WhatsApp plays with sound.
    _TIMEOUT_SECONDS: ClassVar[float] = 60
    _TIMED_OUT: ClassVar[str] = 'ffmpeg timed out'
    # WhatsApp's own audio stickers carry a bit over a minute of audio (60.5s seen).
    _MAX_SECONDS: ClassVar[int] = 65
    # Any member's sticker supplies these files: a crafted one can be an hls or concat
    # playlist that makes ffmpeg fetch URLs or read local files. ffmpeg binds input
    # options to the next -i only, so each input carries its own whitelist.
    _FRAMES_INPUT_ARGS: ClassVar[tuple[str, ...]] = (
        '-protocol_whitelist',
        'file',
        '-format_whitelist',
        'gif,image2',
    )
    _AUDIO_INPUT_ARGS: ClassVar[tuple[str, ...]] = (
        '-protocol_whitelist',
        'file',
        '-format_whitelist',
        'ogg',
        '-f',
        'ogg',
    )
    _ANIMATION_ARGS: ClassVar[tuple[str, ...]] = ('-stream_loop', '-1', '-f', 'gif')
    _STILL_ARGS: ClassVar[tuple[str, ...]] = ('-loop', '1', '-f', 'image2')
    _ENCODE_ARGS: ClassVar[tuple[str, ...]] = (
        '-map',
        '0:v',
        '-map',
        '1:a',
        '-shortest',
        '-t',
        str(_MAX_SECONDS),
        # yuv420p, the pixel format every player decodes, needs even dimensions.
        '-vf',
        'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        '-c:v',
        'libx264',
        # The core node is a 1/8 OCPU VM: trade size for encode time.
        '-preset',
        'veryfast',
        '-pix_fmt',
        'yuv420p',
        '-c:a',
        'aac',
        '-movflags',
        '+faststart',
    )

    @classmethod
    async def render(cls, frames: bytes, audio: bytes, *, animated: bool) -> bytes:
        frames_args = cls._ANIMATION_ARGS if animated else cls._STILL_ARGS
        # Files, not pipes: a looped input is read again from the start, and faststart
        # seeks back to move the index to the front.
        with tempfile.TemporaryDirectory() as directory:
            frames_path = Path(directory) / ('frames.gif' if animated else 'frames.png')
            audio_path = Path(directory) / 'audio.ogg'
            target = Path(directory) / 'video.mp4'
            frames_path.write_bytes(frames)
            audio_path.write_bytes(audio)
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-v',
                'error',
                *cls._FRAMES_INPUT_ARGS,
                *frames_args,
                '-i',
                str(frames_path),
                *cls._AUDIO_INPUT_ARGS,
                '-i',
                str(audio_path),
                *cls._ENCODE_ARGS,
                str(target),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                with anyio.fail_after(cls._TIMEOUT_SECONDS):
                    _, error = await process.communicate()
            except TimeoutError as timeout:
                process.kill()
                raise StickerVideoError(cls._TIMED_OUT) from timeout
            if process.returncode != 0:
                raise StickerVideoError(error.decode().strip())
            return target.read_bytes()
