import asyncio
import tempfile
from pathlib import Path
from typing import ClassVar

import anyio
import httpx
import structlog

from bot.domain.exceptions import VideoThumbnailError
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class VideoThumbnail:
    # Baileys draws a video's thumbnail with ffmpeg, which the edge image lacks, so every
    # video arrived blank (#341). The core has ffmpeg, so it sends one and Baileys keeps it.
    # 32 px wide, as Baileys draws its own: WhatsApp shows it blurred until the video loads.
    _WIDTH: ClassVar[int] = 32
    _TIMEOUT_SECONDS: ClassVar[float] = 15
    _TIMED_OUT: ClassVar[str] = 'ffmpeg timed out'
    # Only the input file, as an mp4 or a jpeg: a crafted video can be a playlist that
    # makes ffmpeg fetch URLs or read local files.
    _INPUT_ARGS: ClassVar[tuple[str, ...]] = (
        '-protocol_whitelist',
        'file',
        '-format_whitelist',
        'mov,jpeg_pipe',
    )
    _FRAME_ARGS: ClassVar[tuple[str, ...]] = (
        '-vf',
        f'scale={_WIDTH}:-1',
        '-frames:v',
        '1',
        '-c:v',
        'mjpeg',
        '-f',
        'image2pipe',
        'pipe:1',
    )

    @classmethod
    async def attach(cls, message: BotMessage) -> None:
        content = message.content
        if not isinstance(content, VideoBufferContent | VideoContent):
            return
        try:
            content.jpeg_thumbnail = await cls._draw(content)
        except VideoThumbnailError as error:
            logger.warning('video_thumbnail_failed', error=str(error))

    @classmethod
    async def _draw(cls, content: VideoBufferContent | VideoContent) -> bytes | None:
        if isinstance(content, VideoBufferContent):
            return await cls._frame(content.data)
        # A URL video has no bytes here, and downloading it all for one frame costs far
        # more than the upstream's preview image.
        if content.thumbnail_url is None:
            return None
        return await cls._frame(await cls._preview(content.thumbnail_url))

    @classmethod
    async def _preview(cls, url: str) -> bytes:
        try:
            return await HttpClient.get_buffer(url, timeout=cls._TIMEOUT_SECONDS)
        except httpx.HTTPError as error:
            # Only the type: an httpx message carries the whole URL.
            raise VideoThumbnailError(type(error).__name__) from error

    @classmethod
    async def _frame(cls, media: bytes) -> bytes:
        # A file, not stdin: an mp4 keeps its index at the end, which a pipe can't seek to.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input'
            source.write_bytes(media)
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-v',
                'error',
                *cls._INPUT_ARGS,
                '-i',
                str(source),
                *cls._FRAME_ARGS,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                with anyio.fail_after(cls._TIMEOUT_SECONDS):
                    output, error = await process.communicate()
            except TimeoutError as timeout:
                process.kill()
                raise VideoThumbnailError(cls._TIMED_OUT) from timeout
        if process.returncode != 0:
            raise VideoThumbnailError(error.decode().strip())
        return output
