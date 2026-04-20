from collections.abc import Iterable, Mapping
from typing import ClassVar

import httpx
import structlog

from bot.data.browser_headers import BROWSER_HEADERS
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class _AudioBufferDefaults:
    MIMETYPE: ClassVar[str] = 'audio/mpeg'
    TYPE: ClassVar[str] = 'audio_mp3'


async def preprocess_messages(messages: Iterable[BotMessage]) -> list[BotMessage]:
    """Download AudioContent/ImageContent URLs into buffer variants for platforms
    that need us to upload bytes rather than hand them a URL. Falls back to the
    original message when the download fails."""
    return [await _preprocess(message) for message in messages]


async def preprocess_for_telegram(messages: Iterable[BotMessage]) -> list[BotMessage]:
    """Telegram-specific preprocessing: shared Audio/Image plus Video URLs and
    RawContent URLs. Telegram's Bot API refuses most CDN URLs that require
    browser headers, so we pre-download them ourselves."""
    shared = await preprocess_messages(messages)
    return [await _preprocess_telegram(message) for message in shared]


async def _preprocess(message: BotMessage) -> BotMessage:
    content = message.content
    if isinstance(content, AudioContent):
        buffer = await _download(content.url)
        if buffer is None:
            return message
        new_content = AudioBufferContent(
            data=buffer,
            mimetype=_AudioBufferDefaults.MIMETYPE,
            type=_AudioBufferDefaults.TYPE,
        )
        return BotMessage(jid=message.jid, content=new_content)
    if isinstance(content, ImageContent):
        buffer = await _download(content.url, headers=BROWSER_HEADERS)
        if buffer is None:
            return message
        new_content = ImageBufferContent(data=buffer, caption=content.caption)
        return BotMessage(jid=message.jid, content=new_content)
    return message


async def _preprocess_telegram(message: BotMessage) -> BotMessage:
    content = message.content
    if isinstance(content, VideoContent):
        buffer = await _download(content.url, headers=BROWSER_HEADERS)
        if buffer is None:
            return message
        return BotMessage(
            jid=message.jid,
            content=VideoBufferContent(data=buffer, caption=content.caption),
        )
    if isinstance(content, RawContent):
        return await _preprocess_raw(message, content)
    return message


async def _preprocess_raw(message: BotMessage, content: RawContent) -> BotMessage:
    raw = content.content
    caption: str | None = raw.get('caption') or None
    gif_playback = bool(raw.get('gifPlayback'))
    url = _raw_video_url(raw) or _raw_image_url(raw)
    if url is None:
        return message
    buffer = await _download(url, headers=BROWSER_HEADERS)
    if buffer is None:
        return message
    if 'video' in raw:
        video = VideoBufferContent(data=buffer, caption=caption, gif_playback=gif_playback)
        return BotMessage(jid=message.jid, content=video)
    if gif_playback:
        animation = VideoBufferContent(data=buffer, caption=caption, gif_playback=True)
        return BotMessage(jid=message.jid, content=animation)
    image = ImageBufferContent(data=buffer, caption=caption)
    return BotMessage(jid=message.jid, content=image)


def _raw_video_url(raw: dict) -> str | None:
    video = raw.get('video')
    if isinstance(video, dict):
        return video.get('url')
    return None


def _raw_image_url(raw: dict) -> str | None:
    image = raw.get('image')
    if isinstance(image, dict):
        return image.get('url')
    return None


async def _download(url: str, headers: Mapping[str, str] | None = None) -> bytes | None:
    try:
        response = await HttpClient.get(url, follow_redirects=True, headers=headers)
    except httpx.HTTPError:
        logger.warning('message_preprocess_download_failed', url=url)
        return None
    return response.content
