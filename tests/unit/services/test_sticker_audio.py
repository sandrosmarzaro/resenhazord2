import shutil
import subprocess
from pathlib import Path

import anyio
import pytest

from bot.domain.exceptions import StickerAudioError
from bot.domain.services.sticker.sticker_audio import StickerAudio

SUBPROCESS = 'bot.domain.services.sticker.sticker_audio.asyncio.create_subprocess_exec'


@pytest.fixture
def fake_tools(mocker):
    def install(*, probed: bytes = b'1\n', encoded: bytes = b'ogg', returncodes=(0, 0)):
        outputs = iter([(probed, b'probe error'), (encoded, b'encode error')])
        codes = iter(returncodes)

        def run(*_args, **_kwargs):
            process = mocker.AsyncMock(returncode=next(codes))
            process.communicate.return_value = next(outputs)
            return process

        return mocker.patch(SUBPROCESS, side_effect=run)

    return install


def _call(tool, index: int) -> tuple[str, ...]:
    return tool.call_args_list[index].args


class TestFromVideo:
    @pytest.mark.anyio
    async def test_returns_the_encoded_audio(self, fake_tools):
        fake_tools(encoded=b'opus')

        assert await StickerAudio.from_video(b'mp4') == b'opus'

    @pytest.mark.anyio
    async def test_returns_nothing_for_a_video_without_audio(self, fake_tools):
        tools = fake_tools(probed=b'')

        audio = await StickerAudio.from_video(b'mp4')

        assert (audio, tools.call_count) == (None, 1)

    @pytest.mark.anyio
    async def test_probes_for_the_first_audio_stream(self, fake_tools):
        tools = fake_tools()

        await StickerAudio.from_video(b'mp4')

        probe = _call(tools, 0)
        assert (probe[0], probe[probe.index('-select_streams') + 1]) == ('ffprobe', 'a:0')

    @pytest.mark.anyio
    async def test_encodes_opus_ogg_as_long_as_a_video_sticker(self, fake_tools):
        tools = fake_tools()

        await StickerAudio.from_video(b'mp4')

        encode = _call(tools, 1)
        assert encode[0] == 'ffmpeg'
        assert encode[encode.index('-t') + 1] == '10'
        assert encode[encode.index('-c:a') + 1] == 'libopus'
        assert encode[encode.index('-f') + 1] == 'ogg'

    @pytest.mark.anyio
    @pytest.mark.parametrize('index', [0, 1])
    async def test_opens_only_a_local_video_file(self, fake_tools, index):
        tools = fake_tools()

        await StickerAudio.from_video(b'mp4')

        args = _call(tools, index)
        whitelist = args.index('-protocol_whitelist')
        assert args[whitelist : whitelist + 4] == (
            '-protocol_whitelist',
            'file',
            '-format_whitelist',
            'mov,avi,matroska',
        )
        assert whitelist < args.index('-i')

    # A phone's AAC track starts with priming samples, which ffmpeg carries into the ogg
    # as negative timestamps; Android then refuses to play the sticker's sound.
    @pytest.mark.anyio
    async def test_starts_the_audio_at_zero(self, fake_tools):
        tools = fake_tools()

        await StickerAudio.from_video(b'mp4')

        encode = _call(tools, 1)
        assert encode[encode.index('-avoid_negative_ts') + 1] == 'make_zero'


class TestErrors:
    @pytest.mark.anyio
    async def test_raises_when_the_probe_fails(self, fake_tools):
        fake_tools(returncodes=(1, 0))

        with pytest.raises(StickerAudioError):
            await StickerAudio.from_video(b'not a video')

    @pytest.mark.anyio
    async def test_raises_when_the_encode_fails(self, fake_tools):
        fake_tools(returncodes=(0, 1))

        with pytest.raises(StickerAudioError):
            await StickerAudio.from_video(b'mp4')

    @pytest.mark.anyio
    async def test_kills_a_tool_that_hangs(self, mocker):
        never = anyio.Event()

        async def hang(*_args):
            await never.wait()

        process = mocker.MagicMock(communicate=hang)
        mocker.patch(SUBPROCESS, return_value=process)
        mocker.patch.object(StickerAudio, '_TIMEOUT_SECONDS', 0.01)

        with pytest.raises(StickerAudioError):
            await StickerAudio.from_video(b'crafted')
        process.kill.assert_called_once_with()


def _video(path: Path, *, with_audio: bool) -> bytes:
    sound = ['-f', 'lavfi', '-i', 'sine=duration=12', '-c:a', 'aac'] if with_audio else []
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'testsrc=size=64x64:rate=10:duration=12',
            *sound,
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            str(path),
        ],
        check=True,
    )
    return path.read_bytes()


def _first_pts(audio: bytes, path: Path) -> int:
    path.write_bytes(audio)
    probed = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-show_packets',
            '-show_entries',
            'packet=pts',
            '-of',
            'csv=p=0',
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(probed.stdout.splitlines()[0].split(',')[0])


def _duration(audio: bytes, path: Path) -> float:
    path.write_bytes(audio)
    probed = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(probed.stdout)


# CI runners have no ffmpeg; the argv tests above cover the same branches there.
@pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg is not installed')
class TestOnFfmpeg:
    # A real subprocess needs the asyncio loop the bot runs on.
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_keeps_ten_seconds_of_a_video_soundtrack(self, tmp_path):
        video = _video(tmp_path / 'sound.mp4', with_audio=True)

        audio = await StickerAudio.from_video(video)

        assert audio is not None
        assert _duration(audio, tmp_path / 'audio.ogg') == pytest.approx(10, abs=0.2)

    @pytest.mark.anyio
    async def test_drops_the_aac_priming_before_zero(self, tmp_path):
        video = _video(tmp_path / 'sound.mp4', with_audio=True)

        audio = await StickerAudio.from_video(video)

        assert audio is not None
        assert _first_pts(audio, tmp_path / 'audio.ogg') == 0

    @pytest.mark.anyio
    async def test_finds_no_audio_in_a_silent_video(self, tmp_path):
        video = _video(tmp_path / 'silent.mp4', with_audio=False)

        assert await StickerAudio.from_video(video) is None
