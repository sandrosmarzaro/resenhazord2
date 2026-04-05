import pytest

from bot.adapters.discord.renderer import DiscordResponseRenderer
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.sticker_content import StickerContent
from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage

def make_message(content) -> BotMessage:
    return BotMessage(jid='test-jid', content=content)


@pytest.fixture
def renderer():
    return DiscordResponseRenderer()


class TestRenderText:
    def test_short_text_returns_text(self, renderer):
        msg = make_message(TextContent(text='hello'))

        reply = renderer.render(msg)

        assert reply.text == 'hello'
        assert reply.embed is None

    def test_long_text_returns_embed(self, renderer):
        text = 'x' * 2001
        msg = make_message(TextContent(text=text))

        reply = renderer.render(msg)

        assert reply.text is None
        assert reply.embed is not None
        assert len(reply.embed.description) <= 4096

    def test_exactly_2000_chars_returns_text(self, renderer):
        text = 'x' * 2000
        msg = make_message(TextContent(text=text))

        reply = renderer.render(msg)

        assert reply.text == text
        assert reply.embed is None


class TestRenderImage:
    def test_sets_embed_image_url(self, renderer):
        msg = make_message(ImageContent(url='https://example.com/img.jpg'))

        reply = renderer.render(msg)

        assert reply.text is None
        assert reply.file is None
        assert reply.embed is not None
        assert reply.embed.image.url == 'https://example.com/img.jpg'

    def test_caption_as_description(self, renderer):
        msg = make_message(ImageContent(url='https://example.com/img.jpg', caption='My caption'))

        reply = renderer.render(msg)

        assert reply.embed.description == 'My caption'

    def test_no_caption_no_description(self, renderer):
        msg = make_message(ImageContent(url='https://example.com/img.jpg'))

        reply = renderer.render(msg)

        assert reply.embed.description is None


class TestRenderImageBuffer:
    def test_creates_file_and_embed(self, renderer):
        msg = make_message(ImageBufferContent(data=b'fake-image'))

        reply = renderer.render(msg)

        assert reply.file is not None
        assert reply.file.filename == 'image.png'
        assert reply.embed is not None
        assert reply.embed.image.url == 'attachment://image.png'

    def test_caption_as_description(self, renderer):
        msg = make_message(ImageBufferContent(data=b'img', caption='A caption'))

        reply = renderer.render(msg)

        assert reply.embed.description == 'A caption'


class TestRenderVideo:
    def test_url_as_text(self, renderer):
        msg = make_message(VideoContent(url='https://example.com/video.mp4'))

        reply = renderer.render(msg)

        assert reply.text == 'https://example.com/video.mp4'
        assert reply.file is None
        assert reply.embed is None

    def test_caption_prepended(self, renderer):
        msg = make_message(VideoContent(url='https://example.com/video.mp4', caption='Watch this'))

        reply = renderer.render(msg)

        assert reply.text == 'Watch this\n\nhttps://example.com/video.mp4'


class TestRenderVideoBuffer:
    def test_creates_file(self, renderer):
        msg = make_message(VideoBufferContent(data=b'fake-video'))

        reply = renderer.render(msg)

        assert reply.file is not None
        assert reply.file.filename == 'video.mp4'

    def test_caption_as_text(self, renderer):
        msg = make_message(VideoBufferContent(data=b'video', caption='Caption'))

        reply = renderer.render(msg)

        assert reply.text == 'Caption'

    def test_no_caption_no_text(self, renderer):
        msg = make_message(VideoBufferContent(data=b'video'))

        reply = renderer.render(msg)

        assert reply.text is None


class TestRenderAudio:
    def test_url_as_text(self, renderer):
        msg = make_message(AudioContent(url='https://example.com/audio.mp3'))

        reply = renderer.render(msg)

        assert reply.text == 'https://example.com/audio.mp3'
        assert reply.file is None


class TestRenderAudioBuffer:
    def test_creates_file(self, renderer):
        msg = make_message(AudioBufferContent(data=b'fake-audio'))

        reply = renderer.render(msg)

        assert reply.file is not None
        assert reply.file.filename == 'audio.mp4'
        assert reply.text is None


class TestRenderUnsupported:
    def test_sticker_returns_fallback_text(self, renderer):
        msg = make_message(StickerContent(data=b'sticker'))

        reply = renderer.render(msg)

        assert reply.text == DiscordResponseRenderer.UNSUPPORTED_MESSAGE
        assert reply.embed is None
        assert reply.file is None

    def test_raw_without_media_returns_fallback_text(self, renderer):
        msg = make_message(RawContent(content={'type': 'buttons'}))

        reply = renderer.render(msg)

        assert reply.text == DiscordResponseRenderer.UNSUPPORTED_MESSAGE


class TestRenderRaw:
    def test_raw_with_video_returns_text_url(self, renderer):
        msg = make_message(RawContent(content={'video': {'url': 'https://example.com/v.mp4'}}))

        reply = renderer.render(msg)

        assert 'https://example.com/v.mp4' in reply.text
        assert reply.embed is None

    def test_raw_video_with_caption_prepends_caption(self, renderer):
        msg = make_message(
            RawContent(content={'video': {'url': 'https://v.com/x.mp4'}, 'caption': 'Watch!'})
        )

        reply = renderer.render(msg)

        assert reply.text == 'Watch!\n\nhttps://v.com/x.mp4'

    def test_raw_with_image_returns_embed(self, renderer):
        msg = make_message(
            RawContent(content={'image': {'url': 'https://example.com/img.jpg'}, 'caption': 'Hi'})
        )

        reply = renderer.render(msg)

        assert reply.embed is not None
        assert reply.embed.image.url == 'https://example.com/img.jpg'
        assert reply.embed.description == 'Hi'

    def test_raw_image_without_caption(self, renderer):
        msg = make_message(RawContent(content={'image': {'url': 'https://example.com/img.jpg'}}))

        reply = renderer.render(msg)

        assert reply.embed is not None
        assert reply.embed.description is None


class TestRenderMany:
    def test_empty_list(self, renderer):
        assert renderer.render_many([]) == []

    def test_multiple_messages(self, renderer):
        messages = [
            make_message(TextContent(text='first')),
            make_message(TextContent(text='second')),
        ]

        replies = renderer.render_many(messages)

        assert len(replies) == 2
        assert replies[0].text == 'first'
        assert replies[1].text == 'second'

    def test_mixed_content_types(self, renderer):
        messages = [
            make_message(TextContent(text='caption')),
            make_message(ImageBufferContent(data=b'img')),
        ]

        replies = renderer.render_many(messages)

        assert replies[0].text == 'caption'
        assert replies[1].file is not None
        assert replies[1].embed is not None
