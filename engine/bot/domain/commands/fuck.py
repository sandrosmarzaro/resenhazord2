import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class FuckCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='fuck',
            args=ArgType.REQUIRED,
            args_pattern=r'^@\d+\s*$',
            args_label='@número',
            group_only=True,
            category='grupo',
        )

    @property
    def menu_description(self) -> str:
        return 'Foda a pessoa mencionada mandando uma foto de pornozão pra ela.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        sender = data.participant or data.sender_jid
        sender_phone = strip_jid(sender)

        mentioned = data.mentioned_jids[0] if data.mentioned_jids else ''
        mentioned_phone = strip_jid(mentioned)

        response = await HttpClient.get(
            'https://nsfwhub.onrender.com/nsfw?type=fuck',
            timeout=30.0,
        )
        response.raise_for_status()
        porn = response.json()
        video_url = porn['image']['url']

        return [
            Reply.to(data).raw(
                {
                    'viewOnce': True,
                    'video': {'url': video_url},
                    'mentions': [sender, mentioned],
                    'caption': f'@{sender_phone} está fudendo @{mentioned_phone} 😩',
                }
            )
        ]
