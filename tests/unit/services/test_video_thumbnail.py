import io
import shutil
import subprocess
from pathlib import Path

import anyio
import httpx
import pytest
from PIL import Image
from structlog.testing import capture_logs

from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage
from bot.domain.services.video_thumbnail import VideoThumbnail

FFMPEG = 'bot.domain.services.video_thumbnail.asyncio.create_subprocess_exec'
PREVIEW_URL = 'https://thumbs.example.com/preview.jpg'


def _video_message() -> BotMessage:
    return BotMessage(jid='g@g.us', content=VideoBufferContent(data=b'mp4'))


@pytest.fixture
def fake_ffmpeg(mocker):
    def install(output: bytes, returncode: int = 0):
        process = mocker.AsyncMock(returncode=returncode)
        process.communicate.return_value = (output, b'Invalid data found')
        return mocker.patch(FFMPEG, return_value=process)

    return install


class TestBufferVideo:
    @pytest.mark.anyio
    async def test_attaches_the_frame_ffmpeg_wrote(self, fake_ffmpeg):
        fake_ffmpeg(b'jpeg')
        message = _video_message()

        await VideoThumbnail.attach(message)

        assert message.content.jpeg_thumbnail == b'jpeg'

    @pytest.mark.anyio
    async def test_scales_one_frame_to_a_32_px_wide_jpeg(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'jpeg')

        await VideoThumbnail.attach(_video_message())

        args = ffmpeg.call_args.args
        assert args[args.index('-i') + 2 :] == (
            '-vf',
            'scale=32:-1',
            '-frames:v',
            '1',
            '-c:v',
            'mjpeg',
            '-f',
            'image2pipe',
            'pipe:1',
        )

    @pytest.mark.anyio
    async def test_opens_only_a_local_mp4_or_jpeg(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'jpeg')

        await VideoThumbnail.attach(_video_message())

        args = ffmpeg.call_args.args
        assert args[: args.index('-i')] == (
            'ffmpeg',
            '-v',
            'error',
            '-protocol_whitelist',
            'file',
            '-format_whitelist',
            'mov,jpeg_pipe',
        )

    @pytest.mark.anyio
    async def test_leaves_other_content_alone(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'jpeg')
        message = BotMessage(jid='g@g.us', content=TextContent('oi'))

        await VideoThumbnail.attach(message)

        ffmpeg.assert_not_called()


class TestUrlVideo:
    @staticmethod
    def _url_message(thumbnail_url: str | None = PREVIEW_URL) -> BotMessage:
        content = VideoContent(url='https://cdn.example.com/v.mp4', thumbnail_url=thumbnail_url)
        return BotMessage(jid='g@g.us', content=content)

    @pytest.mark.anyio
    async def test_scales_the_upstream_preview_with_ffmpeg(self, mocker, respx_mock):
        respx_mock.get(PREVIEW_URL).mock(return_value=httpx.Response(200, content=b'preview'))
        drawn_from: list[bytes] = []
        process = mocker.AsyncMock(returncode=0)
        process.communicate.return_value = (b'jpeg', b'')

        def run(*args, **_kwargs):
            drawn_from.append(Path(args[args.index('-i') + 1]).read_bytes())
            return process

        mocker.patch(FFMPEG, side_effect=run)
        message = self._url_message()

        await VideoThumbnail.attach(message)

        assert drawn_from == [b'preview']
        assert message.content.jpeg_thumbnail == b'jpeg'

    @pytest.mark.anyio
    async def test_skips_a_video_with_no_upstream_preview(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'jpeg')
        message = self._url_message(thumbnail_url=None)

        await VideoThumbnail.attach(message)

        ffmpeg.assert_not_called()
        assert message.content.jpeg_thumbnail is None

    @pytest.mark.anyio
    async def test_sends_the_video_without_a_thumbnail_when_the_preview_fails(
        self, fake_ffmpeg, respx_mock
    ):
        respx_mock.get(PREVIEW_URL).mock(return_value=httpx.Response(404))
        fake_ffmpeg(b'jpeg')
        message = self._url_message()

        with capture_logs() as logs:
            await VideoThumbnail.attach(message)

        assert message.content.jpeg_thumbnail is None
        assert logs == [
            {'event': 'video_thumbnail_failed', 'log_level': 'warning', 'error': 'HTTPStatusError'}
        ]


class TestFailure:
    @pytest.mark.anyio
    async def test_sends_the_video_without_a_thumbnail_when_ffmpeg_fails(self, fake_ffmpeg):
        fake_ffmpeg(b'', returncode=1)
        message = _video_message()

        await VideoThumbnail.attach(message)

        assert message.content.jpeg_thumbnail is None

    @pytest.mark.anyio
    async def test_logs_a_warning_when_ffmpeg_fails(self, fake_ffmpeg):
        fake_ffmpeg(b'', returncode=1)

        with capture_logs() as logs:
            await VideoThumbnail.attach(_video_message())

        assert logs == [
            {
                'event': 'video_thumbnail_failed',
                'log_level': 'warning',
                'error': 'Invalid data found',
            }
        ]

    @pytest.mark.anyio
    async def test_kills_ffmpeg_when_it_hangs(self, mocker):
        never = anyio.Event()

        async def hang(*_args):
            await never.wait()

        process = mocker.MagicMock(communicate=hang)
        mocker.patch(FFMPEG, return_value=process)
        mocker.patch.object(VideoThumbnail, '_TIMEOUT_SECONDS', 0.01)
        message = _video_message()

        await VideoThumbnail.attach(message)

        process.kill.assert_called_once_with()
        assert message.content.jpeg_thumbnail is None


def _encode(path: Path) -> bytes:
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'testsrc=duration=1:size=640x360:rate=25',
            '-frames:v',
            '1',
            '-pix_fmt',
            'yuvj420p',
            str(path),
        ],
        check=True,
    )
    return path.read_bytes()


# CI runners have no ffmpeg; the argv tests above cover the same branches there.
@pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg is not installed')
class TestOnFfmpeg:
    # A real subprocess needs the asyncio loop the bot runs on.
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @staticmethod
    def _width(jpeg: bytes) -> int:
        return Image.open(io.BytesIO(jpeg)).width

    @pytest.mark.anyio
    async def test_draws_a_32_px_jpeg_from_a_real_mp4(self, tmp_path):
        video = _encode(tmp_path / 'video.mp4')
        message = BotMessage(jid='g@g.us', content=VideoBufferContent(data=video))

        await VideoThumbnail.attach(message)

        assert self._width(message.content.jpeg_thumbnail) == 32

    @pytest.mark.anyio
    async def test_scales_a_real_jpeg_preview_to_32_px(self, tmp_path, respx_mock):
        preview = _encode(tmp_path / 'preview.jpg')
        respx_mock.get(PREVIEW_URL).mock(return_value=httpx.Response(200, content=preview))
        content = VideoContent(url='https://cdn.example.com/v.mp4', thumbnail_url=PREVIEW_URL)
        message = BotMessage(jid='g@g.us', content=content)

        await VideoThumbnail.attach(message)

        assert self._width(message.content.jpeg_thumbnail) == 32
