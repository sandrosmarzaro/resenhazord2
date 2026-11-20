from typing import ClassVar

from bot.data.discord import INVITE_PERMISSIONS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand, Platform
from bot.domain.jid import strip_jid
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class LinksCommand(Command):
    TITLE: ClassVar[str] = '*Resenhazord em todo lugar* 🤖'
    WHATSAPP_LINK: ClassVar[str] = '💬 WhatsApp: https://wa.me/{}'
    DISCORD_LINK: ClassVar[str] = (
        '🎮 Discord: https://discord.com/oauth2/authorize?client_id={}'
        f'&scope=bot+applications.commands&permissions={INVITE_PERMISSIONS}'
    )
    TELEGRAM_LINK: ClassVar[str] = '✈️ Telegram: https://t.me/{}'

    def __init__(self, whatsapp_jid: str, discord_app_id: str, telegram_username: str) -> None:
        super().__init__()
        identifiers = {
            self.WHATSAPP_LINK: strip_jid(whatsapp_jid),
            self.DISCORD_LINK: discord_app_id,
            self.TELEGRAM_LINK: telegram_username,
        }
        self._links = [
            link.format(identifier) for link, identifier in identifiers.items() if identifier
        ]

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='links',
            aliases=['convite', 'invite'],
            category=Category.OTHER,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Mostra os links pra me chamar no WhatsApp, Discord e Telegram.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return [Reply.to(data).text('\n'.join([self.TITLE, '', *self._links]))]
