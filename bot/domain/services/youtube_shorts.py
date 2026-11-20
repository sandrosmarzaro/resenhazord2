import asyncio
import json
import re
from typing import Any, ClassVar

from bot.infrastructure.http_client import HttpClient


class YouTubeShorts:
    SEARCH_SIZE: ClassVar[int] = 50
    MAX_DURATION_SECONDS: ClassVar[int] = 60
    # A flat search result carries no width or height, so the tag is what steers it
    # toward Shorts and the duration is the only thing checked.
    SHORTS_TAG: ClassVar[str] = '#shorts'
    # A logged-out visit to the Shorts page opens the feed, and the web client asks the
    # sequence endpoint for the shorts that follow. Neither needs an account.
    FEED_URL: ClassVar[str] = 'https://www.youtube.com/shorts/'
    SEQUENCE_URL: ClassVar[str] = 'https://www.youtube.com/youtubei/v1/reel/reel_watch_sequence'
    SEQUENCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r'"sequenceContinuation":"([^"]+)"')
    WEB_CLIENT: ClassVar[dict[str, str]] = {
        'clientName': 'WEB',
        'clientVersion': '2.20261119.01.00',
    }
    SHORT_URL: ClassVar[str] = 'https://www.youtube.com/shorts/{video_id}'

    @classmethod
    async def search(cls, term: str) -> list[str]:
        process = await asyncio.create_subprocess_exec(
            'yt-dlp',
            '--flat-playlist',
            '--dump-json',
            f'ytsearch{cls.SEARCH_SIZE}:{term} {cls.SHORTS_TAG}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            msg = f'yt-dlp failed: {stderr.decode().strip()}'
            raise RuntimeError(msg)

        entries = [json.loads(line) for line in stdout.decode().splitlines()]
        return [entry['url'] for entry in entries if cls._is_short(entry)]

    @classmethod
    async def feed(cls) -> list[str]:
        page = await HttpClient.get(cls.FEED_URL)
        page.raise_for_status()
        sequence = cls.SEQUENCE_PATTERN.search(page.text)
        if sequence is None:
            msg = 'YouTube Shorts page opened no feed'
            raise RuntimeError(msg)

        response = await HttpClient.post(
            cls.SEQUENCE_URL,
            json={'context': {'client': cls.WEB_CLIENT}, 'sequenceParams': sequence.group(1)},
        )
        response.raise_for_status()
        entries = response.json().get('entries', [])
        if not entries:
            msg = 'YouTube Shorts feed came back empty'
            raise RuntimeError(msg)
        return [
            cls.SHORT_URL.format(video_id=entry['command']['reelWatchEndpoint']['videoId'])
            for entry in entries
        ]

    @classmethod
    def _is_short(cls, entry: dict[str, Any]) -> bool:
        # A live stream has no duration.
        duration = entry.get('duration')
        return duration is not None and duration <= cls.MAX_DURATION_SECONDS
