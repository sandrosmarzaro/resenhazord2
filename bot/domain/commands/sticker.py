from typing import ClassVar

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Category,
    Command,
    CommandConfig,
    OptionDef,
    ParsedCommand,
)
from bot.domain.exceptions import StickerAudioError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.sticker.media_format import MediaFormat
from bot.domain.services.sticker.sticker_audio import StickerAudio
from bot.domain.services.sticker_creator import StickerCreator

logger = structlog.get_logger()


class StickerCommand(Command):
    MEDIA_TYPES = frozenset(('image', 'video', 'sticker'))
    STICKER_TYPES: ClassVar[list[str]] = ['crop', 'full', 'circle', 'rounded']
    QUALITY_PATTERN = r'-?\d{1,2}%?'
    MUTE = 'mute'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='stic',
            aliases=['fig', 'figurinha', 'sticker'],
            options=[
                OptionDef(name='type', values=self.STICKER_TYPES),
                OptionDef(name='quality', pattern=self.QUALITY_PATTERN),
            ],
            flags=[self.MUTE],
            args=ArgType.OPTIONAL,
            args_label='pack | autor',
            category=Category.DOWNLOAD,
        )

    @property
    def menu_description(self) -> str:
        return (
            'Transforme sua imagem anexada em sticker.'
            ' Vídeo vira sticker com áudio, use mute pra vir sem som.'
        )

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if not data.has_media or data.media_type not in self.MEDIA_TYPES:
            return [
                Reply.to(data).text(
                    'Burro burro! Você precisa enviar uma imagem, gif ou sticker'
                    ' para fazer um sticker! 🤦\u200d♂️'
                )
            ]

        sticker_type = parsed.options.get('type', 'full')
        quality_reduction = self._parse_quality_reduction(parsed.options.get('quality'))
        pack, author = self._parse_pack_author(parsed.rest)
        pack = pack or StickerCreator.DEFAULT_PACK
        author = author or StickerCreator.DEFAULT_AUTHOR

        logger.debug(
            'sticker_command',
            jid=data.jid,
            media_type=data.media_type,
            sticker_type=sticker_type,
            quality_reduction=quality_reduction,
            pack=pack,
            author=author,
        )

        buffer = await self._get_media(data)
        sticker = await StickerCreator.create(buffer, sticker_type, quality_reduction)
        audio = None if self.MUTE in parsed.flags else await self._audio(data, buffer)
        return [Reply.to(data).sticker(sticker, pack=pack, author=author, audio=audio)]

    @staticmethod
    async def _audio(data: CommandData, buffer: bytes) -> bytes | None:
        # A quoted audio sticker brings its audio along; a video brings its soundtrack.
        if data.media_audio:
            return data.media_audio
        if not MediaFormat.is_video(buffer):
            return None
        try:
            return await StickerAudio.from_video(buffer)
        except StickerAudioError:
            # The sticker is still worth sending without its sound.
            logger.warning('sticker_audio_failed', jid=data.jid, exc_info=True)
            return None

    @staticmethod
    def _parse_quality_reduction(token: str | None) -> int:
        if not token:
            return 0
        token = token.strip().removeprefix('-').rstrip('%')
        return int(token)

    @staticmethod
    def _parse_pack_author(args: str) -> tuple[str, str]:
        if not args:
            return '', ''
        if '|' in args:
            parts = args.split('|', maxsplit=1)
            return parts[0].strip(), parts[1].strip()
        return args.strip(), ''
