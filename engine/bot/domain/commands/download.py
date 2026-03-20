"""Download video from URL using yt-dlp subprocess."""

import asyncio
import re

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()

URL_REGEX = re.compile(r'https?://\S+')
MAX_BUFFER = 100 * 1024 * 1024  # 100 MB


class YtDlpService:
    """Async wrapper around yt-dlp CLI."""

    @staticmethod
    async def download(url: str) -> tuple[bytes, str]:
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

        if len(video_stdout) > MAX_BUFFER:
            msg = 'Video exceeds maximum buffer size'
            raise ValueError(msg)

        return video_stdout, title


class DownloadCommand(Command):
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
        match = URL_REGEX.search(parsed.rest)
        url = match.group(0) if match else parsed.rest

        try:
            video_buffer, title = await YtDlpService.download(url)
            return [Reply.to(data).video_buffer(video_buffer, title)]
        except Exception:
            logger.exception('download_error', url=url)
            return [Reply.to(data).text('Não consegui baixar esse vídeo 😅')]
