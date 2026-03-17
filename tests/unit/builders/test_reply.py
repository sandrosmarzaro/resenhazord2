"""Port of tests/unit/builders/Reply.test.ts."""

from __future__ import annotations

from bot.domain.builders.reply import Reply
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import (
    AudioContent,
    ImageBufferContent,
    ImageContent,
    RawContent,
    StickerContent,
    TextContent,
    VideoContent,
)


def _make_data(**kwargs) -> CommandData:
    defaults = {
        "text": ",test",
        "jid": "120363000@g.us",
        "sender_jid": "5511900000001@s.whatsapp.net",
        "participant": "5511900000001@s.whatsapp.net",
        "is_group": True,
        "message_id": "MSG_1",
    }
    defaults.update(kwargs)
    return CommandData(**defaults)


class TestReplyText:
    def test_build_text_message(self):
        data = _make_data(expiration=86400)
        msg = Reply.to(data).text("hello")

        assert msg.jid == data.jid
        assert isinstance(msg.content, TextContent)
        assert msg.content.text == "hello"
        assert msg.quoted_message_id == "MSG_1"
        assert msg.expiration == 86400


class TestReplyTextWith:
    def test_build_text_with_mentions(self):
        data = _make_data()
        mentions = ["123@s.whatsapp.net"]
        msg = Reply.to(data).text_with("hello @123", mentions)

        assert isinstance(msg.content, TextContent)
        assert msg.content.text == "hello @123"
        assert msg.content.mentions == mentions


class TestReplyImage:
    def test_build_image_with_view_once(self):
        data = _make_data()
        msg = Reply.to(data).image("https://example.com/img.jpg")

        assert isinstance(msg.content, ImageContent)
        assert msg.content.url == "https://example.com/img.jpg"
        assert msg.content.view_once is True

    def test_include_caption(self):
        data = _make_data()
        msg = Reply.to(data).image("https://example.com/img.jpg", "caption")

        assert isinstance(msg.content, ImageContent)
        assert msg.content.caption == "caption"


class TestReplyImageBuffer:
    def test_build_image_buffer_with_view_once(self):
        data = _make_data()
        buffer = b"fake-image"
        msg = Reply.to(data).image_buffer(buffer, "cap")

        assert isinstance(msg.content, ImageBufferContent)
        assert msg.content.data == buffer
        assert msg.content.caption == "cap"
        assert msg.content.view_once is True


class TestReplyVideo:
    def test_build_video_with_view_once(self):
        data = _make_data()
        msg = Reply.to(data).video("https://example.com/vid.mp4", "vid")

        assert isinstance(msg.content, VideoContent)
        assert msg.content.url == "https://example.com/vid.mp4"
        assert msg.content.caption == "vid"
        assert msg.content.view_once is True


class TestReplyAudio:
    def test_build_audio_with_view_once_and_mimetype(self):
        data = _make_data()
        msg = Reply.to(data).audio("https://example.com/audio.mp3")

        assert isinstance(msg.content, AudioContent)
        assert msg.content.url == "https://example.com/audio.mp3"
        assert msg.content.view_once is True
        assert msg.content.mimetype == "audio/mp4"


class TestReplySticker:
    def test_build_sticker(self):
        data = _make_data()
        buffer = b"fake-sticker"
        msg = Reply.to(data).sticker(buffer)

        assert isinstance(msg.content, StickerContent)
        assert msg.content.data == buffer


class TestReplyRaw:
    def test_build_raw_content(self):
        data = _make_data()
        content = {"image": "x", "caption": "raw"}
        msg = Reply.to(data).raw(content)

        assert msg.jid == data.jid
        assert isinstance(msg.content, RawContent)
        assert msg.content.content == content
        assert msg.quoted_message_id == "MSG_1"


class TestReplyOptions:
    def test_undefined_expiration(self):
        data = _make_data()
        msg = Reply.to(data).text("hi")

        assert msg.expiration is None
