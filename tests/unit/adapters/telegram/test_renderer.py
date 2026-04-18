import pytest

from bot.adapters.telegram.renderer import TelegramResponseRenderer
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.sticker_content import StickerContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage
from bot.ports.telegram_port import TelegramKind

CHAT_ID = 1234


@pytest.fixture
def renderer():
    return TelegramResponseRenderer()


def render(renderer, content):
    return renderer.render(BotMessage(jid='jid', content=content), CHAT_ID)


class TestText:
    def test_single_chunk(self, renderer):
        outbounds = render(renderer, TextContent(text='hello'))

        assert len(outbounds) == 1
        assert outbounds[0].kind == TelegramKind.TEXT
        assert outbounds[0].text == 'hello'

    def test_splits_beyond_limit(self, renderer):
        long_text = 'a' * (renderer.MAX_TEXT_LENGTH + 50)

        outbounds = render(renderer, TextContent(text=long_text))

        assert len(outbounds) == 2
        assert all(out.kind == TelegramKind.TEXT for out in outbounds)
        assert ''.join(out.text or '' for out in outbounds) == long_text


class TestImage:
    def test_url_photo_with_caption(self, renderer):
        outbounds = render(renderer, ImageContent(url='https://x/y.png', caption='cap'))

        assert len(outbounds) == 1
        assert outbounds[0].kind == TelegramKind.PHOTO
        assert outbounds[0].url == 'https://x/y.png'
        assert outbounds[0].text == 'cap'

    def test_buffer_photo_has_filename(self, renderer):
        outbounds = render(renderer, ImageBufferContent(data=b'bytes', caption='cap'))

        assert outbounds[0].kind == TelegramKind.PHOTO
        assert outbounds[0].buffer == b'bytes'
        assert outbounds[0].filename == 'image.png'

    def test_caption_overflow_splits(self, renderer):
        caption = 'x' * (renderer.MAX_CAPTION_LENGTH + 1)

        outbounds = render(renderer, ImageContent(url='https://x/y.png', caption=caption))

        assert len(outbounds) == 2
        assert outbounds[0].kind == TelegramKind.PHOTO
        assert outbounds[0].text is None
        assert outbounds[1].kind == TelegramKind.TEXT
        assert outbounds[1].text == caption


class TestVideo:
    def test_url_video(self, renderer):
        outbounds = render(renderer, VideoContent(url='https://x/y.mp4', caption='cap'))

        assert outbounds[0].kind == TelegramKind.VIDEO
        assert outbounds[0].url == 'https://x/y.mp4'

    def test_buffer_video(self, renderer):
        outbounds = render(renderer, VideoBufferContent(data=b'bytes'))

        assert outbounds[0].kind == TelegramKind.VIDEO
        assert outbounds[0].filename == 'video.mp4'

    def test_gif_playback_routes_to_animation(self, renderer):
        outbounds = render(renderer, VideoBufferContent(data=b'bytes', gif_playback=True))

        assert outbounds[0].kind == TelegramKind.ANIMATION


class TestAudio:
    def test_url_audio(self, renderer):
        outbounds = render(renderer, AudioContent(url='https://x/y.mp3'))

        assert outbounds[0].kind == TelegramKind.AUDIO
        assert outbounds[0].url == 'https://x/y.mp3'

    def test_audio_buffer_default_is_audio(self, renderer):
        outbounds = render(renderer, AudioBufferContent(data=b'bytes'))

        assert outbounds[0].kind == TelegramKind.AUDIO
        assert outbounds[0].filename == 'audio.mp3'

    def test_audio_ogg_buffer_is_voice(self, renderer):
        outbounds = render(renderer, AudioBufferContent(data=b'bytes', type='audio_ogg'))

        assert outbounds[0].kind == TelegramKind.VOICE
        assert outbounds[0].filename == 'audio.ogg'


class TestSticker:
    def test_sticker_from_buffer(self, renderer):
        outbounds = render(renderer, StickerContent(data=b'bytes'))

        assert outbounds[0].kind == TelegramKind.STICKER
        assert outbounds[0].buffer == b'bytes'
        assert outbounds[0].filename == 'sticker.webp'


class TestRaw:
    def test_video_dict_routes_to_video(self, renderer):
        outbounds = render(
            renderer, RawContent(content={'video': {'url': 'https://x/y.mp4'}, 'caption': 'cap'})
        )

        assert outbounds[0].kind == TelegramKind.VIDEO
        assert outbounds[0].url == 'https://x/y.mp4'
        assert outbounds[0].text == 'cap'

    def test_image_dict_routes_to_photo(self, renderer):
        outbounds = render(
            renderer, RawContent(content={'image': {'url': 'https://x/y.png'}})
        )

        assert outbounds[0].kind == TelegramKind.PHOTO
        assert outbounds[0].url == 'https://x/y.png'

    def test_unknown_dict_falls_back_to_unsupported(self, renderer):
        outbounds = render(renderer, RawContent(content={'unexpected': {}}))

        assert outbounds[0].kind == TelegramKind.TEXT
        assert outbounds[0].text == renderer.UNSUPPORTED_MESSAGE


class TestRenderMany:
    def test_concatenates_outbounds(self, renderer):
        messages = [
            BotMessage(jid='jid', content=TextContent(text='one')),
            BotMessage(jid='jid', content=TextContent(text='two')),
        ]

        outbounds = renderer.render_many(messages, CHAT_ID)

        assert [out.text for out in outbounds] == ['one', 'two']
