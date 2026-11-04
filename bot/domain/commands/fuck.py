from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Category,
    Command,
    CommandConfig,
    CommandScope,
    ParsedCommand,
)
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.redgifs import RedGifs


class FuckCommand(Command):
    TAG = 'Sex'

    def __init__(self) -> None:
        super().__init__()
        self._redgifs = RedGifs()

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='fuck',
            args=ArgType.REQUIRED,
            args_pattern=r'^@\d+\s*$',
            args_label='@número',
            group_only=True,
            category=Category.GROUP,
            scope=CommandScope.NSFW,
        )

    @property
    def menu_description(self) -> str:
        return 'Marca alguém e recebe um conteúdo adulto (18+).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        sender = data.participant or data.sender_jid
        sender_phone = strip_jid(sender)

        mentioned = data.mentioned_jids[0] if data.mentioned_jids else ''
        mentioned_phone = strip_jid(mentioned)

        media = await self._redgifs.random_media(self.TAG, video_only=True)

        return [
            Reply.to(data).raw(
                {
                    'viewOnce': True,
                    'video': {'url': media.url},
                    'mentions': [sender, mentioned],
                    'caption': f'@{sender_phone} está fudendo @{mentioned_phone} 😩',
                }
            )
        ]
