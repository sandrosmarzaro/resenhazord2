import json

import httpx
import pytest

from bot.domain.commands.reels import ReelsCommand
from bot.domain.exceptions import DownloadError
from bot.domain.models.message import VideoBufferContent
from tests.factories.command_data import GroupCommandDataFactory

DOWNLOAD_FAILED = 'Não consegui baixar um reels agora, tenta de novo! 😅'
FEED_URL = 'https://www.instagram.com/reels/'
YTDLP_TARGET = 'bot.domain.services.ytdlp.asyncio.create_subprocess_exec'
TITLE = (b'Video by drexlee\n', b'', 0)

# Trimmed from the relay preload of a real logged-out https://www.instagram.com/reels/.
FEED_CODES = ('Df21PhIILQ3', 'Df3RLaPvs3G', 'Df5aqgCJMCr')
FEED = {
    'edges': [
        {
            'node': {
                'pk': '4031987532274095694',
                'code': code,
                'user': {'username': 'drexlee'},
            }
        }
        for code in FEED_CODES
    ],
    'page_info': {'has_next_page': True},
}
PRELOAD = (
    '<script type="application/json" data-sjs>{"require":[["RelayPrefetchedStreamCache","next",[],'
    '["adp_PolarisLoggedOutDesktopWWWClipsContainerQueryRelayPreloader_6b004fac",'
    '{"__bbox":{"complete":true,"result":{"data":{"xig_logged_out_reels_feed":{feed}}}}}]]]}'
    '</script>'
)
FEED_URLS = {f'https://www.instagram.com/reel/{code}/' for code in FEED_CODES}


def _page(feed: dict) -> str:
    return PRELOAD.replace('{feed}', json.dumps(feed))


def _box(kind: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, 'big') + kind + payload


def _mp4(*handlers: bytes) -> bytes:
    tracks = b''.join(_box(b'hdlr', bytes(8) + handler + bytes(12)) for handler in handlers)
    return _box(b'ftyp', b'isom') + _box(b'moov', tracks) + _box(b'mdat', b'frames')


@pytest.fixture
def command():
    return ReelsCommand()


@pytest.fixture
def feed_page(respx_mock):
    return respx_mock.get(FEED_URL).mock(return_value=httpx.Response(200, text=_page(FEED)))


@pytest.fixture
def yt_dlp(mock_subprocess):
    return mock_subprocess(YTDLP_TARGET, calls=[TITLE, (b'video-bytes', b'', 0)])


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',reels', True),
            (', REELS', True),
            (',reels show', True),
            (',reels gato', False),
            ('reels', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestConfig:
    def test_runs_alone_to_bound_memory(self, command):
        assert command.config.exclusive is True


class TestRun:
    @pytest.mark.anyio
    async def test_sends_a_reel_from_the_feed(self, command, feed_page, yt_dlp):
        data = GroupCommandDataFactory.build(text=',reels')

        await command.run(data)

        assert yt_dlp.call_args_list[1][0][-1] in FEED_URLS

    @pytest.mark.anyio
    async def test_sends_the_video_captioned_with_its_title(self, command, feed_page, yt_dlp):
        data = GroupCommandDataFactory.build(text=',reels')

        messages = await command.run(data)

        assert isinstance(messages[0].content, VideoBufferContent)
        assert messages[0].content.data == b'video-bytes'
        assert messages[0].content.caption == 'Video by drexlee'

    @pytest.mark.anyio
    async def test_opens_the_page_as_a_browser_navigation(self, command, feed_page, yt_dlp):
        data = GroupCommandDataFactory.build(text=',reels')

        await command.run(data)

        headers = feed_page.calls.last.request.headers
        assert headers['Sec-Fetch-Mode'] == 'navigate'
        assert headers['Accept'].startswith('text/html')

    @pytest.mark.anyio
    async def test_downloads_with_the_configured_cookies(self, feed_page, yt_dlp):
        command = ReelsCommand(cookies_path='/secrets/cookies.txt')
        data = GroupCommandDataFactory.build(text=',reels')

        await command.run(data)

        download_args = yt_dlp.call_args_list[1][0]
        assert download_args[download_args.index('--cookies') + 1] == '/secrets/cookies.txt'

    @pytest.mark.parametrize(
        ('video', 'gif_playback'),
        [(_mp4(b'vide'), True), (_mp4(b'vide', b'soun'), False)],
        ids=['silent', 'with-audio'],
    )
    @pytest.mark.anyio
    async def test_sends_a_silent_reel_as_gif(
        self, command, feed_page, mock_subprocess, video, gif_playback
    ):
        data = GroupCommandDataFactory.build(text=',reels')
        mock_subprocess(YTDLP_TARGET, calls=[TITLE, (video, b'', 0)])

        messages = await command.run(data)

        assert messages[0].content.gif_playback is gif_playback


class TestErrors:
    @pytest.mark.parametrize(
        'page',
        [
            httpx.Response(200, text='<html><title>Instagram</title></html>'),
            httpx.Response(200, text=_page({'edges': [], 'page_info': {}})),
            httpx.Response(500),
        ],
        ids=['no-feed', 'empty-feed', 'http-error'],
    )
    @pytest.mark.anyio
    async def test_feed_failure_is_a_download_error(self, command, respx_mock, page):
        data = GroupCommandDataFactory.build(text=',reels')
        respx_mock.get(FEED_URL).mock(return_value=page)

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert exc_info.value.user_message == DOWNLOAD_FAILED

    @pytest.mark.anyio
    async def test_download_failure_is_a_download_error(self, command, feed_page, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',reels')
        mock_subprocess(
            YTDLP_TARGET,
            calls=[TITLE, (b'', b'ERROR: [Instagram] Df21PhIILQ3: login required', 1)],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'login required' in str(exc_info.value)
