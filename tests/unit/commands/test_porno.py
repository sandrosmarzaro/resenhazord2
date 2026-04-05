import httpx
import pytest

from bot.domain.commands.porno import PornoCommand
from bot.domain.models.message import RawContent, TextContent, VideoContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return PornoCommand()


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
    async def test_returns_video_for_mp4(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno ia')
        respx_mock.get(url__startswith='https://nsfwhub.onrender.com/').mock(
            return_value=httpx.Response(
                200, json={'image': {'url': 'https://example.com/clip.mp4'}}
            )
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, RawContent)
        content = messages[0].content.content
        assert 'video' in content
        assert content['video']['url'] == 'https://example.com/clip.mp4'
        assert content['viewOnce'] is True

    @pytest.mark.anyio
    async def test_returns_gif_for_gif(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno ia')
        respx_mock.get(url__startswith='https://nsfwhub.onrender.com/').mock(
            return_value=httpx.Response(
                200, json={'image': {'url': 'https://example.com/anim.gif'}}
            )
        )
        messages = await command.run(data)

        content = messages[0].content.content
        assert 'image' in content
        assert content['gifPlayback'] is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno ia show')
        respx_mock.get(url__startswith='https://nsfwhub.onrender.com/').mock(
            return_value=httpx.Response(
                200, json={'image': {'url': 'https://example.com/clip.mp4'}}
            )
        )
        messages = await command.run(data)

        content = messages[0].content.content
        assert content['viewOnce'] is False

    @pytest.mark.anyio
    async def test_returns_image_for_other(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno ia')
        respx_mock.get(url__startswith='https://nsfwhub.onrender.com/').mock(
            return_value=httpx.Response(
                200, json={'image': {'url': 'https://example.com/photo.jpg'}}
            )
        )
        messages = await command.run(data)

        content = messages[0].content.content
        assert 'image' in content
        assert 'gifPlayback' not in content


class TestRealPorn:
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

    @pytest.mark.anyio
    async def test_returns_video_on_success(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno')
        respx_mock.get(url__startswith='https://www.xvideos.com/').mock(
            side_effect=[
                httpx.Response(200, text=self.LISTING_HTML),
                httpx.Response(200, text=self.VIDEO_HTML),
            ]
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, VideoContent)
        assert messages[0].content.url == 'https://cdn.example.com/low.mp4'
        assert messages[0].content.caption == 'Test Video'

    @pytest.mark.anyio
    async def test_returns_error_message_on_failure(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno')
        respx_mock.get(url__startswith='https://www.xvideos.com/').mock(
            side_effect=Exception('Connection error')
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'molhadinho' in messages[0].content.text

    @pytest.mark.anyio
    async def test_raises_when_no_video_links(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno')
        respx_mock.get(url__startswith='https://www.xvideos.com/').mock(
            return_value=httpx.Response(200, text='<html><body>No videos</body></html>')
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)

    @pytest.mark.anyio
    async def test_raises_when_no_video_url_extracted(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno')
        respx_mock.get(url__startswith='https://www.xvideos.com/').mock(
            side_effect=[
                httpx.Response(200, text=self.LISTING_HTML),
                httpx.Response(
                    200,
                    text='<html><head><title>No URL</title></head><body></body></html>',
                ),
            ]
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
