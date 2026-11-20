import json
from pathlib import Path

import httpx
import pytest

from bot.domain.commands.short import ShortCommand
from bot.domain.exceptions import DownloadError
from bot.domain.models.message import TextContent, VideoBufferContent
from tests.factories.command_data import GroupCommandDataFactory

MERGED_FORMAT = 'bv*[vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]'
DOWNLOAD_FAILED = 'Não consegui baixar um short agora, tenta de novo! 😅'
FEED_URL = 'https://www.youtube.com/shorts/'
SEQUENCE_URL = 'https://www.youtube.com/youtubei/v1/reel/reel_watch_sequence'

# Trimmed from a real `yt-dlp --flat-playlist --dump-json "ytsearch5:gato caindo #shorts"`.
SHORT_ENTRY = {
    '_type': 'url',
    'ie_key': 'Youtube',
    'id': 'BC4IgSHz03o',
    'url': 'https://www.youtube.com/watch?v=BC4IgSHz03o',
    'title': 'gato caindo na água 3000x',
    'channel': 'Redpilled Doomer',
    'duration': 31,
}
LONG_ENTRY = {
    '_type': 'url',
    'ie_key': 'Youtube',
    'id': 'v4ps7jmSVsc',
    'url': 'https://www.youtube.com/watch?v=v4ps7jmSVsc',
    'title': 'O MELHOR VÍDEO DE GATOS PULANDO E CAINDO! IMPOSSÍVEL NÃO RIR KKKKKK',
    'channel': 'UnissexTV',
    'duration': 221,
}
LIVE_ENTRY = {**SHORT_ENTRY, 'id': 'live', 'url': 'https://www.youtube.com/watch?v=live'}
LIVE_ENTRY['duration'] = None

# Trimmed from the ytInitialData of a real logged-out https://www.youtube.com/shorts/.
SEQUENCE_PARAMS = (
    'GnAKC29jY19SWmUyVU5FGAAgATC99czq4fuBuQNCUwgAECAaNfIGMgowCgWaAQIQARgBIgIgAerE77wLFRIT'
    'CLW28_fRlpgDFe4cHgAdLMoyhOq6yvMNAggMIgcKBTMyOlNIKg0KC29jY19SWmUyVU5FKgIYDEIAYgRSRFNI'
)
FEED_PAGE = (
    '<script nonce="x">var ytInitialData = {"responseContext":{},'
    '"replacementEndpoint":{"reelWatchEndpoint":{"videoId":"occ_RZe2UNE"}},'
    f'"sequenceContinuation":"{SEQUENCE_PARAMS}"}};</script>'
)
# Trimmed from the real reel_watch_sequence answer to that page.
FEED_IDS = ('HEzlab6sfCg', '8UdWKXeIiII', 'ZHbMehel4l0')
FEED_SEQUENCE = {
    'entries': [
        {
            'command': {
                'commandMetadata': {'webCommandMetadata': {'url': f'/shorts/{video_id}'}},
                'reelWatchEndpoint': {'videoId': video_id},
            }
        }
        for video_id in FEED_IDS
    ],
}
FEED_URLS = {f'https://www.youtube.com/shorts/{video_id}' for video_id in FEED_IDS}


def _search_output(*entries: dict) -> bytes:
    return ''.join(f'{json.dumps(entry)}\n' for entry in entries).encode()


def _box(kind: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, 'big') + kind + payload


def _mp4(*handlers: bytes) -> bytes:
    tracks = b''.join(_box(b'hdlr', bytes(8) + handler + bytes(12)) for handler in handlers)
    return _box(b'ftyp', b'isom') + _box(b'moov', tracks) + _box(b'mdat', b'frames')


@pytest.fixture
def command():
    return ShortCommand()


class FakeYtDlp:
    # Search and download both spawn through asyncio, so one fake answers both runs.
    def __init__(self, mocker) -> None:
        self._mocker = mocker
        self.search = (_search_output(SHORT_ENTRY), b'', 0)
        self.download = (b'video-bytes', b'', 0)
        self.metadata = {'title': SHORT_ENTRY['title'], 'channel': SHORT_ENTRY['channel']}
        self.exec = mocker.patch('asyncio.create_subprocess_exec', side_effect=self._run)

    def args(self, run: int) -> tuple:
        return self.exec.call_args_list[run][0]

    def _run(self, *args, **_kwargs):
        if '--flat-playlist' in args:
            stdout, stderr, returncode = self.search
        else:
            stdout, stderr, returncode = self._download(args)
        process = self._mocker.AsyncMock(returncode=returncode)
        process.communicate.return_value = (stdout, stderr)
        return process

    def _download(self, args: tuple) -> tuple[bytes, bytes, int]:
        video, stderr, returncode = self.download
        # --print alone only simulates; --no-simulate prints and downloads.
        printed = args[args.index('--print') + 1] % self.metadata if '--print' in args else ''
        # yt-dlp merges the streams into the file the output template names.
        if video is not None and '--no-simulate' in args:
            template = args[args.index('-o') + 1]
            Path(template.replace('%(ext)s', 'mp4')).write_bytes(video)
        return f'{printed}\n'.encode(), stderr, returncode


@pytest.fixture
def yt_dlp(mocker):
    return FakeYtDlp(mocker)


@pytest.fixture
def feed_page(respx_mock):
    return respx_mock.get(FEED_URL).mock(return_value=httpx.Response(200, text=FEED_PAGE))


@pytest.fixture
def feed_sequence(respx_mock):
    return respx_mock.post(url__startswith=SEQUENCE_URL).mock(
        return_value=httpx.Response(200, json=FEED_SEQUENCE)
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',short', True),
            (', short', True),
            (', SHORT gato caindo', True),
            (',reels futebol', False),
            (',short show', True),
            ('short', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestConfig:
    def test_runs_alone_to_bound_memory(self, command):
        assert command.config.exclusive is True


class TestRun:
    @pytest.mark.anyio
    async def test_sends_the_short_captioned_with_title_and_channel(self, command, yt_dlp):
        data = GroupCommandDataFactory.build(text=',short gato caindo')

        messages = await command.run(data)

        assert isinstance(messages[0].content, VideoBufferContent)
        assert messages[0].content.data == b'video-bytes'
        assert messages[0].content.caption == 'gato caindo na água 3000x · Redpilled Doomer'

    @pytest.mark.anyio
    async def test_searches_shorts_about_the_term(self, command, yt_dlp):
        data = GroupCommandDataFactory.build(text=',short gato caindo')

        await command.run(data)

        assert yt_dlp.args(0)[-1] == 'ytsearch50:gato caindo #shorts'

    @pytest.mark.anyio
    async def test_skips_videos_over_a_minute_or_without_duration(self, command, yt_dlp):
        data = GroupCommandDataFactory.build(text=',short gato')
        yt_dlp.search = (_search_output(LONG_ENTRY, LIVE_ENTRY, SHORT_ENTRY), b'', 0)

        await command.run(data)

        assert yt_dlp.args(1)[-1] == SHORT_ENTRY['url']

    @pytest.mark.anyio
    async def test_merges_h264_and_aac_into_an_mp4_under_the_cap(self, command, yt_dlp):
        data = GroupCommandDataFactory.build(text=',short gato')

        await command.run(data)

        download_args = yt_dlp.args(1)
        assert download_args[download_args.index('-f') + 1] == MERGED_FORMAT
        assert download_args[download_args.index('--merge-output-format') + 1] == 'mp4'
        assert download_args[download_args.index('--max-filesize') + 1] == '50M'

    @pytest.mark.parametrize(
        ('video', 'gif_playback'),
        [(_mp4(b'vide'), True), (_mp4(b'vide', b'soun'), False)],
        ids=['silent', 'with-audio'],
    )
    @pytest.mark.anyio
    async def test_sends_a_silent_short_as_gif(self, command, yt_dlp, video, gif_playback):
        data = GroupCommandDataFactory.build(text=',short gato')
        yt_dlp.download = (video, b'', 0)

        messages = await command.run(data)

        assert messages[0].content.gif_playback is gif_playback


class TestFeed:
    @pytest.mark.anyio
    async def test_sends_a_short_from_the_feed_without_a_term(
        self, command, yt_dlp, feed_page, feed_sequence
    ):
        data = GroupCommandDataFactory.build(text=',short')

        await command.run(data)

        assert yt_dlp.args(0)[-1] in FEED_URLS

    @pytest.mark.anyio
    async def test_continues_the_feed_the_page_starts(
        self, command, yt_dlp, feed_page, feed_sequence
    ):
        data = GroupCommandDataFactory.build(text=',short')

        await command.run(data)

        body = json.loads(feed_sequence.calls.last.request.content)
        assert body['sequenceParams'] == SEQUENCE_PARAMS
        assert body['context']['client']['clientName'] == 'WEB'

    @pytest.mark.anyio
    async def test_page_without_a_feed_is_a_download_error(self, command, yt_dlp, respx_mock):
        data = GroupCommandDataFactory.build(text=',short')
        respx_mock.get(FEED_URL).mock(return_value=httpx.Response(200, text='<html></html>'))

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert exc_info.value.user_message == DOWNLOAD_FAILED

    @pytest.mark.anyio
    async def test_empty_feed_is_a_download_error(self, command, yt_dlp, feed_page, respx_mock):
        data = GroupCommandDataFactory.build(text=',short')
        respx_mock.post(url__startswith=SEQUENCE_URL).mock(
            return_value=httpx.Response(200, json={'entries': []})
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert exc_info.value.user_message == DOWNLOAD_FAILED

    @pytest.mark.anyio
    async def test_feed_http_failure_is_a_download_error(
        self, command, yt_dlp, feed_page, respx_mock
    ):
        data = GroupCommandDataFactory.build(text=',short')
        respx_mock.post(url__startswith=SEQUENCE_URL).mock(return_value=httpx.Response(500))

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert exc_info.value.user_message == DOWNLOAD_FAILED


class TestNoResults:
    @pytest.mark.parametrize('entries', [(), (LONG_ENTRY,)], ids=['empty', 'only-long-videos'])
    @pytest.mark.anyio
    async def test_says_no_short_was_found(self, command, yt_dlp, entries):
        data = GroupCommandDataFactory.build(text=',short xyzqwkjhasdlkj')
        yt_dlp.search = (_search_output(*entries), b'', 0)

        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert messages[0].content.text == 'Não achei nenhum short sobre *xyzqwkjhasdlkj* 😕'


class TestErrors:
    @pytest.mark.anyio
    async def test_search_failure_is_a_download_error(self, command, yt_dlp):
        data = GroupCommandDataFactory.build(text=',short gato')
        yt_dlp.search = (b'', b"ERROR: [youtube:search] Sign in to confirm you're not a bot", 1)

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert exc_info.value.user_message == DOWNLOAD_FAILED

    @pytest.mark.parametrize(
        ('video', 'returncode'),
        [(b'partial', 1), (None, 0)],
        ids=['yt-dlp-failed', 'over-the-cap'],
    )
    @pytest.mark.anyio
    async def test_download_failure_is_a_download_error(self, command, yt_dlp, video, returncode):
        # An over-cap file aborts with exit 0 and writes nothing.
        data = GroupCommandDataFactory.build(text=',short gato')
        yt_dlp.download = (video, b'ERROR: [youtube] BC4IgSHz03o: Video unavailable', returncode)

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'Video unavailable' in str(exc_info.value)
