import re
from typing import ClassVar
from urllib.parse import urlparse

import httpx
import structlog

from bot.data.download_errors import NO_VIDEO_IN_TWEET
from bot.domain.services.ytdlp import YtDlpService
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class XPhotoService:
    """yt-dlp's X extractor exposes no photos, so photo tweets go through the FxTwitter API."""

    API_URL: ClassVar[str] = 'https://api.fxtwitter.com/status/{status_id}'
    PHOTO_HOST: ClassVar[str] = 'pbs.twimg.com'
    # yt-dlp names the status id in its error whatever the link was (x.com, t.co, ...).
    STATUS_IN_ERROR: ClassVar[re.Pattern[str]] = re.compile(
        rf'\[twitter\] (\d+): {re.escape(NO_VIDEO_IN_TWEET)}'
    )
    # FxTwitter answers 403 to httpx's default python-httpx User-Agent.
    USER_AGENT: ClassVar[str] = 'resenhazord2-bot (+https://github.com/sandrosmarzaro/resenhazord2)'

    @classmethod
    async def download(cls, ytdlp_error: str) -> tuple[list[bytes], str]:
        tweet = await cls._tweet(ytdlp_error)
        photo_urls = [
            photo.get('url', '')
            for photo in (tweet.get('media') or {}).get('photos', [])
            if cls._is_x_photo(photo.get('url', ''))
        ]
        photos = [await cls._fetch(photo_url) for photo_url in photo_urls]
        title = f'{(tweet.get("author") or {}).get("name", "")} - {tweet.get("text", "")}'
        return photos, title

    @classmethod
    async def _tweet(cls, ytdlp_error: str) -> dict:
        match = cls.STATUS_IN_ERROR.search(ytdlp_error)
        if not match:
            return {}
        try:
            response = await HttpClient.get(
                cls.API_URL.format(status_id=match.group(1)),
                headers={'User-Agent': cls.USER_AGENT},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            # A third-party API: when it is down the user still gets the no-video reply.
            logger.warning('x_photo_api_failed', error=str(error))
            return {}
        return response.json().get('tweet') or {}

    @classmethod
    def _is_x_photo(cls, photo_url: str) -> bool:
        photo = urlparse(photo_url)
        return photo.scheme == 'https' and photo.hostname == cls.PHOTO_HOST

    @staticmethod
    async def _fetch(photo_url: str) -> bytes:
        photo = await HttpClient.get_buffer(photo_url)
        if len(photo) > YtDlpService.MAX_BUFFER:
            msg = 'Image exceeds maximum buffer size'
            raise RuntimeError(msg)
        return photo
