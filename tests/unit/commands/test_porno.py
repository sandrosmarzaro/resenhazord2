import httpx
import pytest

from bot.domain.commands.porno import PornoCommand
from bot.domain.models.message import (
    ImageContent,
    TextContent,
    VideoBufferContent,
    VideoContent,
)
from bot.domain.services.mp4_remux import Mp4Remux
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
            (', porno pes', True),
            (', porno pés show dm', True),
            (', porno show', True),
            (', porno dm', True),
            ('  , porno  ', True),
            (',porn', True),
            (', porn gay', True),
            ('porno', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestCategory:
    AUTH_URL = 'https://api.redgifs.com/v2/auth/temporary'
    SEARCH_URL = 'https://api.redgifs.com/v2/gifs/search'
    VIDEO_URL = 'https://media.redgifs.com/Clip-mobile.mp4'

    @pytest.fixture
    def redgifs(self, respx_mock, mocker):
        respx_mock.get(self.AUTH_URL).mock(return_value=httpx.Response(200, json={'token': 't'}))
        respx_mock.get(self.VIDEO_URL).mock(return_value=httpx.Response(200, content=b'm4v'))
        mocker.patch.object(Mp4Remux, 'remux', return_value=b'isom')

        def search_returns(kind: int):
            item = {
                'type': kind,
                'tags': ['Feet'],
                'niches': [],
                'urls': {'sd': self.VIDEO_URL},
            }
            return respx_mock.get(url__startswith=self.SEARCH_URL).mock(
                return_value=httpx.Response(200, json={'gifs': [item]})
            )

        return search_returns

    @pytest.mark.anyio
    async def test_sends_the_remuxed_video_of_the_category(self, command, redgifs):
        redgifs(1)

        messages = await command.run(GroupCommandDataFactory.build(text=', porno pes'))

        assert isinstance(messages[0].content, VideoBufferContent)
        assert messages[0].content.data == b'isom'

    @pytest.mark.anyio
    async def test_sends_an_image_when_the_item_is_one(self, command, redgifs):
        redgifs(2)

        messages = await command.run(GroupCommandDataFactory.build(text=', porno pes'))

        assert isinstance(messages[0].content, ImageContent)

    @pytest.mark.anyio
    async def test_searches_the_tag_behind_the_category(self, command, redgifs):
        search = redgifs(1)

        await command.run(GroupCommandDataFactory.build(text=', porno ruiva'))

        assert search.calls[0].request.url.params['tags'] == 'Redhead'

    @pytest.mark.anyio
    async def test_ignores_accents_and_case(self, command, redgifs):
        search = redgifs(1)

        await command.run(GroupCommandDataFactory.build(text=', porno Pés'))

        assert search.calls[0].request.url.params['tags'] == 'Feet'

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, redgifs):
        redgifs(1)

        messages = await command.run(GroupCommandDataFactory.build(text=', porno pes show'))

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_lists_the_categories_for_an_unknown_one(self, command):
        messages = await command.run(GroupCommandDataFactory.build(text=', porno xyz'))

        text = messages[0].content.text
        assert 'Categoria inválida' in text
        assert 'pes' in text
        assert 'ruiva' in text


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
    AGE_GATED_HTML = """
<html>
<head><title>Test Video - XVIDEOS.COM</title></head>
<body>
<script type="application/ld+json">
{
"@context": "https://schema.org",
"@type": "VideoObject",
"contentUrl": "https://cdn.example.com/sd.mp4?secure=abc==,123"
}
</script>
<script>xv.age_go.init()</script>
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
    async def test_sends_the_content_url_when_the_page_is_age_gated(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', porno')
        respx_mock.get(url__startswith='https://www.xvideos.com/').mock(
            side_effect=[
                httpx.Response(200, text=self.LISTING_HTML),
                httpx.Response(200, text=self.AGE_GATED_HTML),
            ]
        )

        messages = await command.run(data)

        assert messages[0].content.url == 'https://cdn.example.com/sd.mp4?secure=abc==,123'

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
