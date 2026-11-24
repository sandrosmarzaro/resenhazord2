import io
import json
import shutil
import subprocess
from pathlib import Path

import anyio
import pytest
from PIL import Image

from bot.domain.exceptions import StickerVideoError
from bot.domain.services.sticker.sticker_video import StickerVideo

FFMPEG = 'bot.domain.services.sticker.sticker_video.asyncio.create_subprocess_exec'


@pytest.fixture
def fake_ffmpeg(mocker):
    def install(output: bytes, returncode: int = 0):
        process = mocker.AsyncMock(returncode=returncode)
        process.communicate.return_value = (b'', b'Invalid data found')

        def run(*args, **_kwargs):
            Path(args[-1]).write_bytes(output)
            return process

        return mocker.patch(FFMPEG, side_effect=run)

    return install


def _frames_input(args: tuple[str, ...]) -> tuple[str, ...]:
    # The sticker frames are the first input: the options right before its '-i'.
    first = args.index('-i')
    return args[first - 4 : first]


class TestRender:
    @pytest.mark.anyio
    async def test_returns_what_ffmpeg_wrote(self, fake_ffmpeg):
        fake_ffmpeg(b'mp4')

        video = await StickerVideo.render(b'gif', b'ogg', animated=True)

        assert video == b'mp4'

    @pytest.mark.anyio
    async def test_loops_an_animation_under_the_audio(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'mp4')

        await StickerVideo.render(b'gif', b'ogg', animated=True)

        assert _frames_input(ffmpeg.call_args.args) == ('-stream_loop', '-1', '-f', 'gif')

    @pytest.mark.anyio
    async def test_holds_a_still_sticker_under_the_audio(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'mp4')

        await StickerVideo.render(b'png', b'ogg', animated=False)

        assert _frames_input(ffmpeg.call_args.args) == ('-loop', '1', '-f', 'image2')

    @pytest.mark.anyio
    async def test_opens_only_local_image_and_ogg_files(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'mp4')

        await StickerVideo.render(b'gif', b'ogg', animated=True)

        args = ffmpeg.call_args.args
        assert args[:7] == (
            'ffmpeg',
            '-v',
            'error',
            '-protocol_whitelist',
            'file',
            '-format_whitelist',
            'gif,image2,ogg',
        )

    @pytest.mark.anyio
    async def test_ends_with_the_audio_within_65_seconds(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'mp4')

        await StickerVideo.render(b'gif', b'ogg', animated=True)

        args = ffmpeg.call_args.args
        assert '-shortest' in args
        assert args[args.index('-t') + 1] == '65'


class TestErrors:
    @pytest.mark.anyio
    async def test_raises_when_ffmpeg_fails(self, fake_ffmpeg):
        fake_ffmpeg(b'', returncode=1)

        with pytest.raises(StickerVideoError):
            await StickerVideo.render(b'gif', b'not audio', animated=True)

    @pytest.mark.anyio
    async def test_kills_ffmpeg_when_it_hangs(self, mocker):
        never = anyio.Event()

        async def hang(*_args):
            await never.wait()

        process = mocker.MagicMock(communicate=hang)
        mocker.patch(FFMPEG, return_value=process)
        mocker.patch.object(StickerVideo, '_TIMEOUT_SECONDS', 0.01)

        with pytest.raises(StickerVideoError):
            await StickerVideo.render(b'gif', b'ogg', animated=True)
        process.kill.assert_called_once_with()


def _tone(seconds: int) -> bytes:
    return subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            f'sine=frequency=440:duration={seconds}',
            '-c:a',
            'libopus',
            '-f',
            'ogg',
            'pipe:1',
        ],
        check=True,
        capture_output=True,
    ).stdout


def _gif() -> bytes:
    frames = [Image.new('RGB', (64, 64), color) for color in ['red', 'blue']]
    output = io.BytesIO()
    frames[0].save(output, format='GIF', save_all=True, append_images=frames[1:], duration=100)
    return output.getvalue()


def _probe(video: bytes, directory: Path) -> dict:
    path = directory / 'video.mp4'
    path.write_bytes(video)
    probed = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-show_entries',
            'format=duration:stream=codec_name',
            '-of',
            'json',
            str(path),
        ],
        check=True,
        capture_output=True,
    ).stdout
    return json.loads(probed)


# CI runners have no ffmpeg; the argv tests above cover the same branches there.
@pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg is not installed')
class TestOnFfmpeg:
    # A real subprocess needs the asyncio loop the bot runs on.
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_loops_a_short_animation_for_the_whole_audio(self, tmp_path):
        video = await StickerVideo.render(_gif(), _tone(2), animated=True)

        probed = _probe(video, tmp_path)
        assert {stream['codec_name'] for stream in probed['streams']} == {'h264', 'aac'}
        assert float(probed['format']['duration']) == pytest.approx(2, abs=0.3)
