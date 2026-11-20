import asyncio
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from bot.data.youtube_domains import YOUTUBE_DOMAINS
from bot.domain.exceptions import DownloadError
from bot.infrastructure.http_client import HttpClient


class YtDlpService:
    MAX_BUFFER = 100 * 1024 * 1024  # 100 MB
    MAX_FILESIZE = '50M'
    # H.264 and AAC, which every WhatsApp client plays.
    MERGED_FORMAT = 'bv*[vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]'
    CAPTION_TEMPLATE = '%(title)s · %(channel)s'
    # Signed-in YouTube needs its player's n challenge solved; the image ships Bun.
    JS_RUNTIME = 'bun'
    IMAGE_HOST_SUFFIX = '.fbcdn.net'

    @classmethod
    async def download(cls, url: str, cookies_path: str = '') -> tuple[bytes, str]:
        cookies = cls._cookie_args(cookies_path)

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
        if cls._is_youtube(url):
            video, _ = await cls.download_merged(url, cookies_path)
            return video, title

        video_proc = await asyncio.create_subprocess_exec(
            'yt-dlp',
            *cookies,
            '--playlist-items',
            '1',
            '-f',
            'best[ext=mp4]/best',
            # Pick the best format under the cap; --max-filesize alone aborts on the top one.
            '-S',
            f'size:{cls.MAX_FILESIZE}',
            '--max-filesize',
            cls.MAX_FILESIZE,
            '-o',
            '-',
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        video_stdout, video_stderr = await video_proc.communicate()

        # An over-cap file aborts with exit 0 and an empty stdout.
        if video_proc.returncode != 0 or not video_stdout:
            error_msg = video_stderr.decode().strip()
            msg = f'yt-dlp failed: {error_msg}'
            raise RuntimeError(msg)

        if len(video_stdout) > cls.MAX_BUFFER:
            msg = 'Video exceeds maximum buffer size'
            raise DownloadError(msg)

        return video_stdout, title

    @classmethod
    async def download_merged(cls, url: str, cookies_path: str = '') -> tuple[bytes, str]:
        # YouTube no longer serves one mp4 with both streams, and yt-dlp merges into
        # stdout only as MPEG-TS, so the streams merge into an mp4 file first.
        cookies = cls._cookie_args(cookies_path)
        with tempfile.TemporaryDirectory() as directory:
            process = await asyncio.create_subprocess_exec(
                'yt-dlp',
                *cookies,
                '--js-runtimes',
                cls.JS_RUNTIME,
                # The caption rides the same run; --print alone would skip the download.
                '--no-simulate',
                '--print',
                cls.CAPTION_TEMPLATE,
                '--playlist-items',
                '1',
                '-f',
                cls.MERGED_FORMAT,
                '-S',
                f'size:{cls.MAX_FILESIZE}',
                '--max-filesize',
                cls.MAX_FILESIZE,
                '--merge-output-format',
                'mp4',
                '-o',
                str(Path(directory) / 'video.%(ext)s'),
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            video = Path(directory) / 'video.mp4'
            # An over-cap file aborts with exit 0 and writes nothing.
            if process.returncode != 0 or not video.exists():
                msg = f'yt-dlp failed: {stderr.decode().strip()}'
                raise RuntimeError(msg)
            return video.read_bytes(), stdout.decode().strip()

    @staticmethod
    def _cookie_args(cookies_path: str) -> list[str]:
        return ['--cookies', cookies_path] if cookies_path else []

    @staticmethod
    def _is_youtube(url: str) -> bool:
        host = urlparse(url).hostname or ''
        return any(host == domain or host.endswith(f'.{domain}') for domain in YOUTUBE_DOMAINS)

    @classmethod
    async def download_image(cls, url: str, cookies_path: str = '') -> tuple[bytes, str]:
        cookies = cls._cookie_args(cookies_path)

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

        title, *_, image_url = stdout.decode().splitlines()
        image = urlparse(image_url)
        if image.scheme != 'https' or not (image.hostname or '').endswith(cls.IMAGE_HOST_SUFFIX):
            msg = f'Unexpected image host: {image.hostname}'
            raise RuntimeError(msg)

        image_buffer = await HttpClient.get_buffer(image_url)
        if len(image_buffer) > cls.MAX_BUFFER:
            msg = 'Image exceeds maximum buffer size'
            raise RuntimeError(msg)

        return image_buffer, title
