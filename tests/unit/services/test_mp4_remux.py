from pathlib import Path

import anyio
import pytest

from bot.domain.exceptions import VideoRemuxError
from bot.domain.services.mp4_remux import Mp4Remux

FFMPEG = 'bot.domain.services.mp4_remux.asyncio.create_subprocess_exec'


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


class TestRemux:
    @pytest.mark.anyio
    async def test_returns_what_ffmpeg_wrote(self, fake_ffmpeg):
        fake_ffmpeg(b'isom-mp4')

        video = await Mp4Remux.remux(b'm4v-mp4')

        assert video == b'isom-mp4'

    @pytest.mark.anyio
    async def test_copies_the_streams_into_a_faststart_mp4(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'isom-mp4')

        await Mp4Remux.remux(b'm4v-mp4')

        args = ffmpeg.call_args.args
        assert args[args.index('-i') + 2 : -1] == ('-c', 'copy', '-movflags', '+faststart')

    @pytest.mark.anyio
    async def test_opens_only_a_local_mp4(self, fake_ffmpeg):
        ffmpeg = fake_ffmpeg(b'isom-mp4')

        await Mp4Remux.remux(b'm4v-mp4')

        args = ffmpeg.call_args.args
        assert args[: args.index('-i')] == (
            'ffmpeg',
            '-v',
            'error',
            '-protocol_whitelist',
            'file',
            '-format_whitelist',
            'mov',
        )


class TestErrors:
    @pytest.mark.anyio
    async def test_raises_when_ffmpeg_fails(self, fake_ffmpeg):
        fake_ffmpeg(b'', returncode=1)

        with pytest.raises(VideoRemuxError):
            await Mp4Remux.remux(b'not a video')

    @pytest.mark.anyio
    async def test_kills_ffmpeg_when_it_hangs(self, mocker):
        never = anyio.Event()

        async def hang(*_args):
            await never.wait()

        process = mocker.MagicMock(communicate=hang)
        mocker.patch(FFMPEG, return_value=process)
        mocker.patch.object(Mp4Remux, '_TIMEOUT_SECONDS', 0.01)

        with pytest.raises(VideoRemuxError):
            await Mp4Remux.remux(b'crafted')
        process.kill.assert_called_once_with()
