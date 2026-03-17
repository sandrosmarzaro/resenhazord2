from unittest.mock import patch

import pytest

from bot.domain.commands.porno import PornoCommand
from bot.domain.models.message import RawContent, TextContent, VideoContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_html_response, make_json_response


@pytest.fixture
def command():
    return PornoCommand()


def _mock_nsfw_response(url='https://example.com/video.mp4'):
    return make_json_response({'image': {'url': url}})


LISTING_HTML = """
<div class="thumb-block">
    <a href="/video.abc123/first-video">video 1</a>
</div>
<div class="thumb-block">
    <a href="/video.def456/second-video">video 2</a>
</div>
"""

VIDEO_HTML = """
<html>
<head><title>Test Video - XVIDEOS.COM</title></head>
<body>
<script>setVideoUrlLow('https://cdn.example.com/low.mp4')</script>
<script>setVideoUrlHigh('https://cdn.example.com/high.mp4')</script>
</body>
</html>
"""


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', porno', True),
            (',porno', True),
            (', PORNO', True),
            (', porno ia', True),
            (', porno show', True),
            (', porno dm', True),
            (', porno ia show dm', True),
            ('  , porno  ', True),
            ('porno', False),
            ('hello', False),
            (', porno extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestIaPorn:
    @pytest.mark.anyio
    async def test_returns_video_for_mp4(self, command):
        data = GroupCommandDataFactory.build(text=', porno ia')
        resp = _mock_nsfw_response('https://example.com/clip.mp4')

        with patch('bot.domain.commands.porno.HttpClient.get', return_value=resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, RawContent)
        content = messages[0].content.content
        assert 'video' in content
        assert content['video']['url'] == 'https://example.com/clip.mp4'
        assert content['viewOnce'] is True

    @pytest.mark.anyio
    async def test_returns_gif_for_gif(self, command):
        data = GroupCommandDataFactory.build(text=', porno ia')
        resp = _mock_nsfw_response('https://example.com/anim.gif')

        with patch('bot.domain.commands.porno.HttpClient.get', return_value=resp):
            messages = await command.run(data)

        content = messages[0].content.content
        assert 'image' in content
        assert content['gifPlayback'] is True

    @pytest.mark.anyio
    async def test_returns_image_for_other(self, command):
        data = GroupCommandDataFactory.build(text=', porno ia')
        resp = _mock_nsfw_response('https://example.com/photo.jpg')

        with patch('bot.domain.commands.porno.HttpClient.get', return_value=resp):
            messages = await command.run(data)

        content = messages[0].content.content
        assert 'image' in content
        assert 'gifPlayback' not in content


class TestRealPorn:
    @pytest.mark.anyio
    async def test_returns_video_on_success(self, command):
        data = GroupCommandDataFactory.build(text=', porno')
        listing_resp = make_html_response(LISTING_HTML)
        video_resp = make_html_response(VIDEO_HTML)

        with patch(
            'bot.domain.commands.porno.HttpClient.get',
            side_effect=[listing_resp, video_resp],
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, VideoContent)
        assert messages[0].content.url == 'https://cdn.example.com/low.mp4'
        assert messages[0].content.caption == 'Test Video'

    @pytest.mark.anyio
    async def test_returns_error_message_on_failure(self, command):
        data = GroupCommandDataFactory.build(text=', porno')

        with patch(
            'bot.domain.commands.porno.HttpClient.get',
            side_effect=Exception('Connection error'),
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'molhadinho' in messages[0].content.text

    @pytest.mark.anyio
    async def test_raises_when_no_video_links(self, command):
        data = GroupCommandDataFactory.build(text=', porno')
        listing_resp = make_html_response('<html><body>No videos</body></html>')

        with patch('bot.domain.commands.porno.HttpClient.get', return_value=listing_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)

    @pytest.mark.anyio
    async def test_raises_when_no_video_url_extracted(self, command):
        data = GroupCommandDataFactory.build(text=', porno')
        listing_resp = make_html_response(LISTING_HTML)
        video_resp = make_html_response(
            '<html><head><title>No URL</title></head><body></body></html>'
        )

        with patch(
            'bot.domain.commands.porno.HttpClient.get',
            side_effect=[listing_resp, video_resp],
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
