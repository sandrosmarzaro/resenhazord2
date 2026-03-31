import asyncio
from pathlib import Path
from typing import ClassVar

import structlog

from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.track import Track

logger = structlog.get_logger()


class YtDlpAudioService:
    AUDIO_FORMAT: ClassVar[str] = 'bestaudio/best'
    COOKIES_PATH: ClassVar[Path] = Path('/app/cookies.txt')
    JS_RUNTIME: ClassVar[str] = 'bun'
    MAX_PLAYLIST_TRACKS: ClassVar[int] = 200
    YOUTUBE_VIDEO_BASE: ClassVar[str] = 'https://www.youtube.com/watch?v='

    @classmethod
    def _base_args(cls) -> list[str]:
        args = ['yt-dlp', '--js-runtimes', cls.JS_RUNTIME]
        if cls.COOKIES_PATH.is_file():
            args.extend(['--cookies', str(cls.COOKIES_PATH)])
        return args

    @classmethod
    async def resolve_stream(cls, query: str, *, requested_by: str, requested_by_id: int) -> Track:
        proc = await asyncio.create_subprocess_exec(
            *cls._base_args(),
            '-f',
            cls.AUDIO_FORMAT,
            '--no-playlist',
            '--print',
            'urls',
            '--print',
            'title',
            '--print',
            'uploader',
            '--print',
            'duration',
            '--print',
            'thumbnail',
            '--print',
            'original_url',
            query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.warning('ytdlp_resolve_failed', query=query, error=error_msg)
            msg = 'Nao consegui carregar essa musica'
            raise ExternalServiceError(msg, detail=error_msg)

        lines = stdout.decode().strip().splitlines()
        expected_lines = 6
        if len(lines) < expected_lines:
            msg = 'Nao consegui obter informacoes dessa musica'
            raise ExternalServiceError(msg)

        stream_url, title, author, raw_duration, thumbnail, original_url = (
            lines[0],
            lines[1],
            lines[2],
            lines[3],
            lines[4],
            lines[5],
        )

        return Track(
            title=title or 'Desconhecido',
            author=author or 'Desconhecido',
            url=original_url or query,
            stream_url=stream_url,
            duration=cls._parse_duration(raw_duration),
            thumbnail=thumbnail or '',
            requested_by=requested_by,
            requested_by_id=requested_by_id,
        )

    @classmethod
    async def search(
        cls, query: str, *, limit: int = 3, requested_by: str, requested_by_id: int
    ) -> list[Track]:
        search_query = f'ytsearch{limit}:{query}'

        proc = await asyncio.create_subprocess_exec(
            *cls._base_args(),
            '-f',
            cls.AUDIO_FORMAT,
            '--flat-playlist',
            '--print',
            'id',
            '--print',
            'title',
            '--print',
            'uploader',
            '--print',
            'duration',
            '--print',
            'thumbnail',
            search_query,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.warning('ytdlp_search_failed', query=query, error=error_msg)
            msg = 'Nao consegui buscar musicas'
            raise ExternalServiceError(msg, detail=error_msg)

        lines = stdout.decode().strip().splitlines()
        fields_per_track = 5
        tracks: list[Track] = []

        for i in range(0, len(lines), fields_per_track):
            chunk = lines[i : i + fields_per_track]
            if len(chunk) < fields_per_track:
                break

            video_id, title, author, raw_duration, thumbnail = chunk
            tracks.append(
                Track(
                    title=title or 'Desconhecido',
                    author=author or 'Desconhecido',
                    url=f'{cls.YOUTUBE_VIDEO_BASE}{video_id}',
                    stream_url='',
                    duration=cls._parse_duration(raw_duration),
                    thumbnail=thumbnail or '',
                    requested_by=requested_by,
                    requested_by_id=requested_by_id,
                )
            )

        return tracks

    @classmethod
    async def resolve_playlist(
        cls, url: str, *, requested_by: str, requested_by_id: int
    ) -> list[Track]:
        proc = await asyncio.create_subprocess_exec(
            *cls._base_args(),
            '--flat-playlist',
            '--print',
            'id',
            '--print',
            'title',
            '--print',
            'uploader',
            '--print',
            'duration',
            '--print',
            'thumbnail',
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.warning('ytdlp_playlist_failed', url=url, error=error_msg)
            msg = 'Nao consegui carregar essa playlist'
            raise ExternalServiceError(msg, detail=error_msg)

        lines = stdout.decode().strip().splitlines()
        fields_per_track = 5
        tracks: list[Track] = []

        for i in range(0, len(lines), fields_per_track):
            if len(tracks) >= cls.MAX_PLAYLIST_TRACKS:
                break

            chunk = lines[i : i + fields_per_track]
            if len(chunk) < fields_per_track:
                break

            video_id, title, author, raw_duration, thumbnail = chunk
            tracks.append(
                Track(
                    title=title or 'Desconhecido',
                    author=author or 'Desconhecido',
                    url=f'{cls.YOUTUBE_VIDEO_BASE}{video_id}',
                    stream_url='',
                    duration=cls._parse_duration(raw_duration),
                    thumbnail=thumbnail or '',
                    requested_by=requested_by,
                    requested_by_id=requested_by_id,
                )
            )

        return tracks

    @staticmethod
    def _parse_duration(raw: str) -> int:
        try:
            return int(float(raw))
        except (ValueError, TypeError):
            return 0
