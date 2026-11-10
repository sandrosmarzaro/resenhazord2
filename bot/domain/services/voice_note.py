import asyncio
import tempfile
from pathlib import Path
from typing import ClassVar

import anyio

from bot.domain.exceptions import VoiceNoteError
from bot.domain.models.message import AudioBufferContent, AudioContent, BotMessage
from bot.infrastructure.http_client import HttpClient


class VoiceNote:
    # A group status carries audio only as a voice note, and WhatsApp plays a voice
    # note only as ogg/opus: any other format shows "something is wrong with the file".
    MIMETYPE: ClassVar[str] = 'audio/ogg; codecs=opus'
    # Any member can hand ffmpeg a file: cap how much of it is read and how long it runs.
    _MAX_SECONDS: ClassVar[int] = 600
    _TIMEOUT_SECONDS: ClassVar[float] = 60
    _TIMED_OUT: ClassVar[str] = 'ffmpeg timed out'
    # A crafted "audio" can be an hls or concat playlist that makes ffmpeg fetch URLs
    # or read local files: open only the input file, as one of the audio containers.
    _INPUT_ARGS: ClassVar[tuple[str, ...]] = (
        '-protocol_whitelist',
        'file',
        '-format_whitelist',
        'mp3,ogg,mov,wav,aac,flac,matroska,amr',
    )
    _ENCODE_ARGS: ClassVar[tuple[str, ...]] = (
        '-t',
        str(_MAX_SECONDS),
        '-vn',
        '-ac',
        '1',
        '-ar',
        '48000',
        '-c:a',
        'libopus',
        '-b:a',
        '64k',
        '-f',
        'ogg',
        'pipe:1',
    )

    @classmethod
    async def for_status(cls, message: BotMessage) -> BotMessage:
        content = message.content
        if not message.group_status or not isinstance(content, AudioContent | AudioBufferContent):
            return message
        audio = (
            content.data
            if isinstance(content, AudioBufferContent)
            else await HttpClient.get_buffer(content.url)
        )
        message.content = AudioBufferContent(data=await cls._encode(audio), mimetype=cls.MIMETYPE)
        return message

    @classmethod
    async def _encode(cls, audio: bytes) -> bytes:
        # A file, not stdin: an mp4 keeps its index at the end, which a pipe can't seek to.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input'
            source.write_bytes(audio)
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-v',
                'error',
                *cls._INPUT_ARGS,
                '-i',
                str(source),
                *cls._ENCODE_ARGS,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                with anyio.fail_after(cls._TIMEOUT_SECONDS):
                    output, error = await process.communicate()
            except TimeoutError as timeout:
                process.kill()
                raise VoiceNoteError(cls._TIMED_OUT) from timeout
        if process.returncode != 0:
            raise VoiceNoteError(error.decode().strip())
        return output
