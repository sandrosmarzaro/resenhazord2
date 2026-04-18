from collections.abc import Iterable, Mapping
from typing import Final

import httpx
import structlog

from bot.data.browser_headers import BROWSER_HEADERS
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

_AUDIO_MIMETYPE: Final[str] = 'audio/mpeg'
_AUDIO_TYPE: Final[str] = 'audio_mp3'


async def preprocess_messages(messages: Iterable[BotMessage]) -> list[BotMessage]:
    """Download AudioContent/ImageContent URLs into buffer variants for platforms
    that need us to upload bytes rather than hand them a URL. Falls back to the
    original message when the download fails."""
    return [await _preprocess(message) for message in messages]


async def _preprocess(message: BotMessage) -> BotMessage:
    content = message.content
    if isinstance(content, AudioContent):
        buffer = await _download(content.url)
        if buffer is None:
            return message
        new_content = AudioBufferContent(data=buffer, mimetype=_AUDIO_MIMETYPE, type=_AUDIO_TYPE)
        return BotMessage(jid=message.jid, content=new_content)
    if isinstance(content, ImageContent):
        buffer = await _download(content.url, headers=BROWSER_HEADERS)
        if buffer is None:
            return message
        new_content = ImageBufferContent(data=buffer, caption=content.caption)
        return BotMessage(jid=message.jid, content=new_content)
    return message


async def _download(url: str, headers: Mapping[str, str] | None = None) -> bytes | None:
    try:
        response = await HttpClient.get(url, follow_redirects=True, headers=headers)
    except httpx.HTTPError:
        logger.warning('message_preprocess_download_failed', url=url)
        return None
    return response.content
