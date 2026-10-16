import asyncio

from bot.domain.exceptions import DownloadError
from bot.infrastructure.http_client import HttpClient


class YtDlpService:
    MAX_BUFFER = 100 * 1024 * 1024  # 100 MB

    @classmethod
    async def download(cls, url: str, cookies_path: str = '') -> tuple[bytes, str]:
        cookies = ['--cookies', cookies_path] if cookies_path else []

        title_proc = await asyncio.create_subprocess_exec(
            'yt-dlp',
            *cookies,
            '--playlist-items',
            '1',
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
            *cookies,
            '--playlist-items',
            '1',
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
            raise DownloadError(msg)

        return video_stdout, title

    @classmethod
    async def download_image(cls, url: str, cookies_path: str = '') -> tuple[bytes, str]:
        cookies = ['--cookies', cookies_path] if cookies_path else []

        # Photo posts have no formats; the full-size photo is the best thumbnail.
        proc = await asyncio.create_subprocess_exec(
            'yt-dlp',
            *cookies,
            '--ignore-no-formats-error',
            '--playlist-items',
            '1',
            '--print',
            'title',
            '--print',
            'thumbnail',
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            msg = f'yt-dlp failed: {stderr.decode().strip()}'
            raise RuntimeError(msg)

        lines = stdout.decode().splitlines()
        return await HttpClient.get_buffer(lines[-1]), lines[0]
