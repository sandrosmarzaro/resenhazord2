import asyncio
import re

import structlog

from bot.data.download_errors import (
    FALLBACK_MESSAGE,
    FILE_TOO_LARGE_MESSAGE,
    YTDLP_ERROR_MESSAGES,
)
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.exceptions import DownloadError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()


class YtDlpService:
    MAX_BUFFER = 100 * 1024 * 1024  # 100 MB

    @classmethod
    async def download(cls, url: str) -> tuple[bytes, str]:
        title_proc = await asyncio.create_subprocess_exec(
            'yt-dlp',
            '--print',
            'title',
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        title_stdout, _ = await title_proc.communicate()
        title = title_stdout.decode().strip() or 'Vídeo'

        video_proc = await asyncio.create_subprocess_exec(
            'yt-dlp',
            '-f',
            'best[ext=mp4]/best',
            '--max-filesize',
            '50m',
            '-o',
            '-',
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        video_stdout, video_stderr = await video_proc.communicate()

        if video_proc.returncode != 0:
            error_msg = video_stderr.decode().strip()
            msg = f'yt-dlp failed: {error_msg}'
            raise RuntimeError(msg)

        if len(video_stdout) > cls.MAX_BUFFER:
            msg = 'Video exceeds maximum buffer size'
            raise ValueError(msg)

        return video_stdout, title


class DownloadCommand(Command):
    URL_REGEX = re.compile(r'https?://\S+')

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='dl',
            aliases=['baixar'],
            flags=['show', 'dm'],
            args=ArgType.REQUIRED,
            args_pattern=r'https?://\S+[\s\S]*',
            category='download',
        )

    @property
    def menu_description(self) -> str:
        return 'Baixe vídeos de qualquer URL (YouTube, Instagram, TikTok, etc.).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        match = self.URL_REGEX.search(parsed.rest)
        url = match.group(0) if match else parsed.rest

        try:
            video_buffer, title = await YtDlpService.download(url)
        except RuntimeError as e:
            raise DownloadError(self._match_error(str(e)), detail=str(e)) from e
        except ValueError as e:
            raise DownloadError(FILE_TOO_LARGE_MESSAGE, detail=str(e)) from e
        except Exception as e:
            raise DownloadError(FALLBACK_MESSAGE, detail=str(e)) from e

        return [Reply.to(data).video_buffer(video_buffer, title)]

    @staticmethod
    def _match_error(error: str) -> str:
        for pattern, message in YTDLP_ERROR_MESSAGES.items():
            if pattern in error:
                return message
        return FALLBACK_MESSAGE
