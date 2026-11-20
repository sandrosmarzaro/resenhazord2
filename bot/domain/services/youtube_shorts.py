import asyncio
import json
from typing import Any, ClassVar

from bot.data.youtube_short import YouTubeShort


class YouTubeShorts:
    SEARCH_SIZE: ClassVar[int] = 50
    MAX_DURATION_SECONDS: ClassVar[int] = 60
    # A flat search result carries no width or height, so the tag is what steers it
    # toward Shorts and the duration is the only thing checked.
    SHORTS_TAG: ClassVar[str] = '#shorts'

    @classmethod
    async def search(cls, term: str) -> list[YouTubeShort]:
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
        return [
            YouTubeShort(url=entry['url'], title=entry['title'], channel=entry['channel'])
            for entry in entries
            if cls._is_short(entry)
        ]

    @classmethod
    def _is_short(cls, entry: dict[str, Any]) -> bool:
        # A live stream has no duration.
        duration = entry.get('duration')
        return duration is not None and duration <= cls.MAX_DURATION_SECONDS
