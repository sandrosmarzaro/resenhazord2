from collections.abc import Callable
from typing import ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Category, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import (
    AudioBufferContent,
    BotMessage,
    ImageBufferContent,
    MessageContent,
    TextContent,
    VideoBufferContent,
)

type MediaContent = Callable[[bytes, str | None], MessageContent]


class GroupStatusCommand(Command):
    USAGE: ClassVar[str] = (
        'Responda a uma imagem, vídeo, áudio ou texto com *,status*, '
        'ou mande *,status <texto>* pra eu postar no status do grupo! 📸'
    )
    UNSUPPORTED_MEDIA: ClassVar[str] = 'Status de grupo só aceita imagem, vídeo, áudio ou texto! 😅'
    # A status voice note is always ptt, and WhatsApp's own voice notes are ogg/opus.
    VOICE_MIMETYPE: ClassVar[str] = 'audio/ogg; codecs=opus'
    MEDIA_CONTENTS: ClassVar[dict[str, MediaContent]] = {
        'image': lambda data, caption: ImageBufferContent(
            data=data, caption=caption, view_once=False
        ),
        'video': lambda data, caption: VideoBufferContent(
            data=data, caption=caption, view_once=False
        ),
        'audio': lambda data, _caption: AudioBufferContent(
            data=data, mimetype=GroupStatusCommand.VOICE_MIMETYPE
        ),
    }

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='status',
            args=ArgType.OPTIONAL,
            args_label='texto',
            group_only=True,
            category=Category.GROUP,
        )

    @property
    def menu_description(self) -> str:
        return 'Posta a mídia ou o texto respondido, ou o texto dado, no status do grupo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if data.media_type:
            return await self._post_media(data, parsed.rest or data.media_caption)
        text = parsed.rest or data.quoted_text
        if not text:
            return [Reply.to(data).text(self.USAGE)]
        return [self._status(data, TextContent(text=text))]

    async def _post_media(self, data: CommandData, caption: str | None) -> list[BotMessage]:
        content = self.MEDIA_CONTENTS.get(data.media_type or '')
        if content is None:
            return [Reply.to(data).text(self.UNSUPPORTED_MEDIA)]
        buffer = await self._get_media(data)
        return [self._status(data, content(buffer, caption))]

    @staticmethod
    def _status(data: CommandData, content: MessageContent) -> BotMessage:
        return BotMessage(jid=data.jid, content=content, group_status=True)
