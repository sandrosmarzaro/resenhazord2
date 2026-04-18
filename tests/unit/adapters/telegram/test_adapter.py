import pytest
from telegram import Bot, InputFile
from telegram.constants import ChatAction

from bot.adapters.telegram.adapter import TelegramBotAdapter
from bot.ports.telegram_port import TelegramKind, TelegramOutbound


@pytest.fixture
def bot(mocker):
    return mocker.AsyncMock(spec=Bot)


@pytest.fixture
def adapter(bot):
    return TelegramBotAdapter(bot)


class TestSend:
    @pytest.mark.anyio
    async def test_text_routes_to_send_message(self, adapter, bot):
        await adapter.send(TelegramOutbound(kind=TelegramKind.TEXT, chat_id=1, text='hi'))

        bot.send_message.assert_called_once_with(chat_id=1, text='hi')

    @pytest.mark.anyio
    async def test_photo_with_url_passes_url(self, adapter, bot):
        await adapter.send(
            TelegramOutbound(kind=TelegramKind.PHOTO, chat_id=1, url='https://x/y.png')
        )

        bot.send_photo.assert_called_once_with(chat_id=1, photo='https://x/y.png')

    @pytest.mark.anyio
    async def test_photo_with_buffer_and_filename_wraps_input_file(self, adapter, bot):
        await adapter.send(
            TelegramOutbound(
                kind=TelegramKind.PHOTO, chat_id=1, buffer=b'bytes', filename='image.png'
            )
        )

        bot.send_photo.assert_called_once()
        kwargs = bot.send_photo.call_args.kwargs
        assert kwargs['chat_id'] == 1
        assert isinstance(kwargs['photo'], InputFile)

    @pytest.mark.anyio
    async def test_caption_sent_when_text_on_media(self, adapter, bot):
        await adapter.send(
            TelegramOutbound(kind=TelegramKind.PHOTO, chat_id=1, url='https://x/y.png', text='cap')
        )

        kwargs = bot.send_photo.call_args.kwargs
        assert kwargs['caption'] == 'cap'

    @pytest.mark.anyio
    async def test_sticker_ignores_caption(self, adapter, bot):
        await adapter.send(
            TelegramOutbound(kind=TelegramKind.STICKER, chat_id=1, buffer=b'bytes', text='ignored')
        )

        kwargs = bot.send_sticker.call_args.kwargs
        assert 'caption' not in kwargs

    @pytest.mark.anyio
    async def test_voice_routes_to_send_voice(self, adapter, bot):
        await adapter.send(TelegramOutbound(kind=TelegramKind.VOICE, chat_id=1, buffer=b'bytes'))

        bot.send_voice.assert_called_once()

    @pytest.mark.anyio
    async def test_missing_url_and_buffer_raises(self, adapter):
        with pytest.raises(ValueError, match='missing both url and buffer'):
            await adapter.send(TelegramOutbound(kind=TelegramKind.PHOTO, chat_id=1))


class TestSendTyping:
    @pytest.mark.anyio
    async def test_calls_send_chat_action(self, adapter, bot):
        await adapter.send_typing(99)

        bot.send_chat_action.assert_called_once_with(chat_id=99, action=ChatAction.TYPING)
