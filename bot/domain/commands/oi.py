from typing import ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand, Platform
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class OiCommand(Command):
    NATIVE_MENTION_PLATFORMS: ClassVar[frozenset[str]] = frozenset(
        {Platform.DISCORD, Platform.TELEGRAM}
    )

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='oi',
            aliases=['hi'],
            category=Category.OTHER,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Apenas diga oi ao bot.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if data.platform in self.NATIVE_MENTION_PLATFORMS:
            mention = self._format_mention(data)
            return [Reply.to(data).text(f'Vai se foder {mention} filho da puta! 🖕')]
        sender = data.participant or data.sender_jid
        sender_phone = strip_jid(sender)
        text = f'Vai se fuder @{sender_phone} filho da puta! 🖕'
        return [Reply.to(data).text_with(text, [sender])]

    @staticmethod
    def _format_mention(data: CommandData) -> str:
        if data.platform == Platform.DISCORD:
            return f'<@{data.sender_jid}>'
        return data.push_name or 'filho da puta'
