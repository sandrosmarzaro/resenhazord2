from io import BytesIO
from typing import Any, ClassVar

from telegram import Bot, InputFile, ReactionTypeEmoji
from telegram.constants import ChatAction, ParseMode

from bot.ports.telegram_port import TelegramKind, TelegramOutbound


class TelegramBotAdapter:
    _MEDIA_KWARG: ClassVar[dict[TelegramKind, str]] = {
        TelegramKind.PHOTO: 'photo',
        TelegramKind.VIDEO: 'video',
        TelegramKind.AUDIO: 'audio',
        TelegramKind.VOICE: 'voice',
        TelegramKind.DOCUMENT: 'document',
        TelegramKind.STICKER: 'sticker',
        TelegramKind.ANIMATION: 'animation',
    }

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send(self, outbound: TelegramOutbound) -> None:
        if outbound.kind == TelegramKind.TEXT:
            await self._bot.send_message(
                chat_id=outbound.chat_id,
                text=outbound.text or '',
                parse_mode=ParseMode.HTML,
            )
            return
        await self._send_media(outbound)

    async def send_typing(self, chat_id: int) -> None:
        await self._bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    async def react(self, chat_id: int, message_id: int, emoji: str) -> None:
        await self._bot.set_message_reaction(
            chat_id=chat_id, message_id=message_id, reaction=[ReactionTypeEmoji(emoji=emoji)]
        )

    async def _send_media(self, outbound: TelegramOutbound) -> None:
        method = getattr(self._bot, f'send_{outbound.kind.value}')
        kwargs: dict[str, Any] = {
            'chat_id': outbound.chat_id,
            self._MEDIA_KWARG[outbound.kind]: self._resolve_media(outbound),
        }
        if outbound.text and outbound.kind != TelegramKind.STICKER:
            kwargs['caption'] = outbound.text
            kwargs['parse_mode'] = ParseMode.HTML
        await method(**kwargs)

    @staticmethod
    def _resolve_media(outbound: TelegramOutbound) -> str | InputFile | bytes:
        if outbound.url is not None:
            return outbound.url
        if outbound.buffer is None:
            message = f'TelegramOutbound(kind={outbound.kind}) missing both url and buffer'
            raise ValueError(message)
        if outbound.filename is not None:
            return InputFile(BytesIO(outbound.buffer), filename=outbound.filename)
        return outbound.buffer
