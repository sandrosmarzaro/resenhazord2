from typing import ClassVar

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage

logger = structlog.get_logger()


class StickerCommand(Command):
    MEDIA_TYPES = frozenset(('image', 'video'))
    STICKER_TYPES: ClassVar[list[str]] = ['crop', 'full', 'circle', 'rounded']

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='stic',
            options=[OptionDef(name='type', values=self.STICKER_TYPES)],
            category='download',
        )

    @property
    def menu_description(self) -> str:
        return 'Transforme sua imagem anexada em sticker.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if not data.has_media or data.media_type not in self.MEDIA_TYPES:
            return [
                Reply.to(data).text(
                    'Burro burro! Você precisa enviar uma imagem ou gif'
                    ' para fazer um sticker! 🤦\u200d♂️'
                )
            ]

        sticker_type = parsed.options.get('type', 'full')

        logger.info(
            'sticker_command',
            jid=data.jid,
            media_type=data.media_type,
            sticker_type=sticker_type,
        )

        buffer = await self._whatsapp.download_media(data.message_id, data.media_source)
        sticker = await self._whatsapp.create_sticker(buffer, sticker_type)
        return [Reply.to(data).sticker(sticker)]
