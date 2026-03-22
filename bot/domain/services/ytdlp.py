import asyncio

from bot.domain.exceptions import DownloadError


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
            raise DownloadError(msg)

        return video_stdout, title
