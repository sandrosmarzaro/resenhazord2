from typing import Self

from bot.domain.models.command_data import CommandData
from bot.domain.models.message import (
    AudioBufferContent,
    AudioContent,
    BotMessage,
    ImageBufferContent,
    ImageContent,
    RawContent,
    StickerContent,
    TextContent,
    VideoBufferContent,
    VideoContent,
)


class Reply:
    def __init__(self, data: CommandData) -> None:
        self._jid = data.jid
        self._quoted = data.message_id
        self._expiration = data.expiration

    @classmethod
    def to(cls, data: CommandData) -> Self:
        return cls(data)

    def text(self, text: str) -> BotMessage:
        return self._build(TextContent(text=text))

    def text_with(self, text: str, mentions: list[str]) -> BotMessage:
        return self._build(TextContent(text=text, mentions=mentions))

    def image(self, url: str, caption: str | None = None) -> BotMessage:
        return self._build(ImageContent(url=url, caption=caption, view_once=True))

    def image_buffer(self, data: bytes, caption: str | None = None) -> BotMessage:
        return self._build(ImageBufferContent(data=data, caption=caption, view_once=True))

    def video(self, url: str, caption: str | None = None) -> BotMessage:
        return self._build(VideoContent(url=url, caption=caption, view_once=True))

    def video_buffer(
        self, data: bytes, caption: str | None = None, *, gif_playback: bool = False
    ) -> BotMessage:
        content = VideoBufferContent(
            data=data, caption=caption, view_once=True, gif_playback=gif_playback
        )
        return self._build(content)

    def audio(self, url: str) -> BotMessage:
        return self._build(AudioContent(url=url, view_once=True))

    def audio_buffer(self, data: bytes, mimetype: str = 'audio/mp4') -> BotMessage:
        return self._build(AudioBufferContent(data=data, mimetype=mimetype))

    def sticker(self, data: bytes, pack: str = '', author: str = '') -> BotMessage:
        return self._build(StickerContent(data=data, pack=pack, author=author))

    def raw(self, content: dict) -> BotMessage:
        return self._build(RawContent(content=content))

    def _build(
        self,
        content: TextContent
        | ImageContent
        | ImageBufferContent
        | VideoContent
        | VideoBufferContent
        | AudioContent
        | AudioBufferContent
        | StickerContent
        | RawContent,
    ) -> BotMessage:
        return BotMessage(
            jid=self._jid,
            content=content,
            quoted_message_id=self._quoted,
            expiration=self._expiration,
        )
