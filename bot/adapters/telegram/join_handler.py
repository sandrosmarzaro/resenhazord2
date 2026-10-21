from typing import ClassVar

from telegram import Update
from telegram.constants import ChatMemberStatus, ChatType

from bot.adapters.telegram.formatter import WhatsAppHtmlFormatter
from bot.data.welcome_messages import TELEGRAM_WELCOME
from bot.ports.telegram_port import TelegramKind, TelegramOutbound, TelegramPort


class TelegramJoinHandler:
    GROUP_CHAT_TYPES: ClassVar[frozenset[str]] = frozenset({ChatType.GROUP, ChatType.SUPERGROUP})
    OUTSIDE_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}
    )

    async def handle(self, port: TelegramPort, update: Update) -> None:
        change = update.my_chat_member
        if change is None or change.chat.type not in self.GROUP_CHAT_TYPES:
            return
        was_outside = change.old_chat_member.status in self.OUTSIDE_STATUSES
        is_outside = change.new_chat_member.status in self.OUTSIDE_STATUSES
        if not was_outside or is_outside:
            return
        text = WhatsAppHtmlFormatter.to_html(TELEGRAM_WELCOME)
        await port.send(TelegramOutbound(kind=TelegramKind.TEXT, chat_id=change.chat.id, text=text))
