from typing import ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand, Platform
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class OiCommand(Command):
    GREETING: ClassVar[str] = (
        'Oi {mention}! 👋 Que bom te ver! Manda ,menu que eu te mostro tudo que sei fazer 😄'
    )
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
        return 'Diga oi e ganhe as boas-vindas do bot.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if data.platform in self.NATIVE_MENTION_PLATFORMS:
            return [Reply.to(data).text(self.GREETING.format(mention=self._format_mention(data)))]

        # WhatsApp only renders mentions inside groups; in a private chat an @number shows
        # up as raw text, so greet the person by name instead.
        if not data.is_group:
            return [Reply.to(data).text(self.GREETING.format(mention=data.push_name or 'você'))]

        sender = data.participant or data.sender_jid
        text = self.GREETING.format(mention=f'@{strip_jid(sender)}')
        return [Reply.to(data).text_with(text, [sender])]

    @staticmethod
    def _format_mention(data: CommandData) -> str:
        if data.platform == Platform.DISCORD:
            return f'<@{data.sender_jid}>'
        return data.push_name or 'amigo'
