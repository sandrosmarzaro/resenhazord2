from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class OiCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='oi', aliases=['hi'], category=Category.OTHER)

    @property
    def menu_description(self) -> str:
        return 'Apenas diga oi ao bot.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        sender = data.participant or data.sender_jid
        sender_phone = strip_jid(sender)
        text = f'Vai se fuder @{sender_phone} filho da puta! 🖕'
        return [Reply.to(data).text_with(text, [sender])]
