import io
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from bot.data.sticker import MAX_ANIMATED_STICKER_BYTES, STICKER_SIZE
from bot.domain.services.sticker.frame_shaper import FrameShaper
from bot.domain.services.sticker.media_format import MediaFormat
from bot.domain.services.sticker_creator import StickerCreator

VIDEO_BUFFER = b'\x00\x00\x00\x1c' + b'ftyp' + b'isom' + b'\x00' * 100


@pytest.fixture
def ffmpeg_argv(mocker) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []
    proc = mocker.AsyncMock()
    proc.communicate.return_value = (b'', b'')
    proc.returncode = 0

    def fake_exec(*args, **_kwargs):
        calls.append(args)
        Path(args[-1]).write_bytes(b'fake-webp')
        return proc

    mocker.patch('asyncio.create_subprocess_exec', side_effect=fake_exec)
    return calls


def _create_noise_webp(n_frames: int) -> bytes:
    frames = [
        Image.frombytes('RGBA', (512, 512), os.urandom(512 * 512 * 4)) for _ in range(n_frames)
    ]
    buf = io.BytesIO()
    frames[0].save(buf, format='WEBP', save_all=True, append_images=frames[1:], duration=100)
    return buf.getvalue()


def _create_test_image(width: int = 100, height: int = 80, color: str = 'red') -> bytes:
    img = Image.new('RGBA', (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _create_animated_webp(
    width: int = 100,
    height: int = 80,
    colors: tuple[str, ...] = ('red', 'blue', 'green'),
) -> bytes:
    frames = [Image.new('RGBA', (width, height), c) for c in colors]
    buf = io.BytesIO()
    frames[0].save(
        buf,
        format='WEBP',
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )
    return buf.getvalue()


def _create_static_webp(width: int = 100, height: int = 80, color: str = 'red') -> bytes:
    img = Image.new('RGBA', (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format='WEBP')
    return buf.getvalue()


class TestStickerCreatorImage:
    @staticmethod
    def _webp_to_image(webp_bytes: bytes) -> Image.Image:
        return Image.open(io.BytesIO(webp_bytes))

    @pytest.mark.anyio
    async def test_full_creates_512x512_webp(self) -> None:
        result = await StickerCreator.create(_create_test_image(), 'full')
        img = self._webp_to_image(result)
        assert img.size == (512, 512)

    @pytest.mark.anyio
    async def test_crop_creates_512x512_webp(self) -> None:
        result = await StickerCreator.create(_create_test_image(), 'crop')
        img = self._webp_to_image(result)
        assert img.size == (512, 512)

    @pytest.mark.anyio
    async def test_circle_creates_512x512_webp(self) -> None:
        result = await StickerCreator.create(_create_test_image(), 'circle')
        img = self._webp_to_image(result)
        assert img.size == (512, 512)

    @pytest.mark.anyio
    async def test_circle_has_transparent_corners(self) -> None:
        result = await StickerCreator.create(_create_test_image(color='blue'), 'circle')
        img = self._webp_to_image(result).convert('RGBA')
        pixel = img.getpixel((0, 0))
        assert isinstance(pixel, tuple)
        assert pixel[3] == 0

    @pytest.mark.anyio
    async def test_rounded_creates_512x512_webp(self) -> None:
        result = await StickerCreator.create(_create_test_image(), 'rounded')
        img = self._webp_to_image(result)
        assert img.size == (512, 512)

    @pytest.mark.anyio
    async def test_rounded_has_transparent_corners(self) -> None:
        result = await StickerCreator.create(_create_test_image(color='green'), 'rounded')
        img = self._webp_to_image(result).convert('RGBA')
        pixel = img.getpixel((0, 0))
        assert isinstance(pixel, tuple)
        assert pixel[3] == 0

    @pytest.mark.anyio
    async def test_full_preserves_aspect_ratio(self) -> None:
        result = await StickerCreator.create(_create_test_image(200, 100), 'full')
        img = self._webp_to_image(result).convert('RGBA')
        assert img.size == (512, 512)
        center_pixel = img.getpixel((256, 256))
        assert isinstance(center_pixel, tuple)
        assert center_pixel[3] > 0

    @pytest.mark.anyio
    async def test_default_type_is_full(self) -> None:
        default_result = await StickerCreator.create(_create_test_image())
        full_result = await StickerCreator.create(_create_test_image(), 'full')
        assert self._webp_to_image(default_result).size == self._webp_to_image(full_result).size

    def test_pixelate_produces_block_regions(self) -> None:
        img = Image.new('RGBA', STICKER_SIZE, 'red')
        for x in range(img.width):
            for y in range(img.height):
                img.putpixel((x, y), (x % 256, y % 256, 128, 255))

        result = FrameShaper._pixelate(img, working_size=32)

        assert result.size == STICKER_SIZE
        block = STICKER_SIZE[0] // 32
        assert result.getpixel((0, 0)) == result.getpixel((block - 1, block - 1))

    @pytest.mark.anyio
    async def test_quality_reduction_passed_to_pil(self, mocker) -> None:
        save_spy = mocker.spy(Image.Image, 'save')

        await StickerCreator.create(_create_test_image(), 'full', quality_reduction=50)

        assert save_spy.call_args.kwargs['quality'] == 25

    @pytest.mark.anyio
    async def test_quality_reduction_floors_at_min(self, mocker) -> None:
        save_spy = mocker.spy(Image.Image, 'save')

        await StickerCreator.create(_create_test_image(), 'full', quality_reduction=99)

        assert save_spy.call_args.kwargs['quality'] >= StickerCreator.MIN_WEBP_QUALITY

    def test_effective_quality_no_reduction(self) -> None:
        assert StickerCreator._effective_quality(0) == StickerCreator.WEBP_QUALITY

    def test_effective_quality_half_reduction(self) -> None:
        assert StickerCreator._effective_quality(50) == 25

    def test_effective_quality_never_below_min(self) -> None:
        assert StickerCreator._effective_quality(99) >= StickerCreator.MIN_WEBP_QUALITY

    def test_effective_working_size_no_reduction(self) -> None:
        assert StickerCreator._effective_working_size(0) == STICKER_SIZE[0]

    def test_effective_working_size_half_reduction(self) -> None:
        assert StickerCreator._effective_working_size(50) == 256

    def test_effective_working_size_never_below_min(self) -> None:
        assert StickerCreator._effective_working_size(99) >= StickerCreator.MIN_WORKING_SIZE


class TestStickerCreatorVideo:
    @pytest.mark.anyio
    async def test_video_calls_ffmpeg(self, mocker) -> None:
        img = Image.new('RGBA', (512, 512), 'red')
        buf = io.BytesIO()
        img.save(buf, format='WEBP')
        webp_bytes = buf.getvalue()

        mock_proc = mocker.AsyncMock()
        mock_proc.communicate.return_value = (b'', b'')
        mock_proc.returncode = 0

        def write_fake_output(*args, **_kwargs):
            Path(args[-1]).write_bytes(webp_bytes)

        def fake_exec(*args, **_kwargs):
            write_fake_output(*args)
            return mock_proc

        mock_exec = mocker.patch(
            'asyncio.create_subprocess_exec',
            side_effect=fake_exec,
        )
        video_buffer = b'\x00\x00\x00\x1c' + b'ftyp' + b'isom' + b'\x00' * 100

        await StickerCreator.create(video_buffer, 'full')

        mock_exec.assert_called_once()
        call_args = mock_exec.call_args[0]
        assert call_args[0] == 'ffmpeg'
        assert '-vcodec' in call_args
        assert 'libwebp' in call_args
        assert '-quality' in call_args

    @pytest.mark.anyio
    async def test_video_quality_reduction_passed_to_ffmpeg(self, mocker) -> None:
        img = Image.new('RGBA', (512, 512), 'red')
        buf = io.BytesIO()
        img.save(buf, format='WEBP')
        webp_bytes = buf.getvalue()

        mock_proc = mocker.AsyncMock()
        mock_proc.communicate.return_value = (b'', b'')
        mock_proc.returncode = 0

        def write_fake_output(*args, **_kwargs):
            Path(args[-1]).write_bytes(webp_bytes)

        def fake_run(*args, **_kwargs):
            write_fake_output(*args)
            return mock_proc

        mock_run = mocker.patch(
            'asyncio.create_subprocess_exec',
            side_effect=fake_run,
        )
        video_buffer = b'\x00\x00\x00\x1c' + b'ftyp' + b'isom' + b'\x00' * 100

        await StickerCreator.create(video_buffer, 'full', quality_reduction=80)

        call_args = mock_run.call_args[0]
        quality_index = call_args.index('-quality')
        assert call_args[quality_index + 1] == '10'

    @pytest.mark.anyio
    async def test_video_ffmpeg_error_propagates(self, mocker) -> None:
        mock_proc = mocker.AsyncMock()
        mock_proc.communicate.return_value = (b'', b'conversion failed')
        mock_proc.returncode = 1
        mocker.patch(
            'asyncio.create_subprocess_exec',
            return_value=mock_proc,
        )
        video_buffer = b'\x00\x00\x00\x1c' + b'ftyp' + b'isom' + b'\x00' * 100

        with pytest.raises(RuntimeError, match='ffmpeg failed'):
            await StickerCreator.create(video_buffer, 'full')


@pytest.fixture(scope='module')
def landscape_video(tmp_path_factory) -> bytes:
    path = tmp_path_factory.mktemp('video') / 'landscape.mp4'
    subprocess.run(
        [
            'ffmpeg',
            '-loglevel',
            'error',
            '-f',
            'lavfi',
            '-i',
            'color=red:size=640x480:rate=15',
            '-t',
            '1',
            '-pix_fmt',
            'yuv420p',
            str(path),
        ],
        check=True,
    )
    return path.read_bytes()


# CI runners have no ffmpeg; the argv tests below cover the same branches there.
@pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg is not installed')
class TestVideoShapesOnFfmpeg:
    # A real subprocess needs the asyncio loop the bot runs on.
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @staticmethod
    def _alpha(webp: bytes, xy: tuple[int, int]) -> int:
        pixel = Image.open(io.BytesIO(webp)).convert('RGBA').getpixel(xy)
        assert isinstance(pixel, tuple)
        return pixel[3]

    @pytest.mark.anyio
    async def test_full_pads_a_landscape_video_with_transparency(self, landscape_video) -> None:
        result = await StickerCreator.create(landscape_video, 'full')

        assert self._alpha(result, (256, 5)) == 0
        assert self._alpha(result, (256, 256)) == 255

    @pytest.mark.anyio
    async def test_crop_fills_the_whole_sticker(self, landscape_video) -> None:
        result = await StickerCreator.create(landscape_video, 'crop')

        assert self._alpha(result, (0, 0)) == 255
        assert self._alpha(result, (256, 5)) == 255

    @pytest.mark.anyio
    async def test_circle_clears_everything_outside_the_circle(self, landscape_video) -> None:
        result = await StickerCreator.create(landscape_video, 'circle')

        assert self._alpha(result, (0, 0)) == 0
        assert self._alpha(result, (20, 20)) == 0
        assert self._alpha(result, (256, 5)) == 255

    @pytest.mark.anyio
    async def test_rounded_clears_only_the_corners(self, landscape_video) -> None:
        result = await StickerCreator.create(landscape_video, 'rounded')

        assert self._alpha(result, (0, 0)) == 0
        assert self._alpha(result, (20, 20)) == 255
        assert self._alpha(result, (5, 256)) == 255


class TestVideoFfmpegCommand:
    FULL_FILTER = (
        'format=rgba,scale=512:512:force_original_aspect_ratio=decrease:flags=bilinear,'
        'fps=15,pad=512:512:-1:-1:color=0x00000000,scale=512:512:flags=neighbor'
    )

    @pytest.mark.anyio
    async def test_full_video_runs_the_expected_ffmpeg_command(self, ffmpeg_argv) -> None:
        await StickerCreator.create(VIDEO_BUFFER, 'full')

        argv = ffmpeg_argv[0]
        assert argv[:2] == ('ffmpeg', '-i')
        assert argv[3:-1] == (
            '-vcodec',
            'libwebp',
            '-vf',
            self.FULL_FILTER,
            '-quality',
            '50',
            '-loop',
            '0',
            '-t',
            '10',
            '-preset',
            'default',
            '-an',
            '-vsync',
            '0',
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('sticker_type', 'shape'),
        [
            ('crop', ''),
            (
                'circle',
                ",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*lte(hypot(X+0.5-W/2,Y+0.5-H/2),W/2)'",
            ),
            (
                'rounded',
                ",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                "a='255*lte(hypot(max(0,max(W/8-X-0.5,X+0.5-W+W/8)),"
                "max(0,max(H/8-Y-0.5,Y+0.5-H+H/8))),W/8)'",
            ),
        ],
    )
    async def test_shaped_video_is_cropped_and_masked(
        self, ffmpeg_argv, sticker_type, shape
    ) -> None:
        await StickerCreator.create(VIDEO_BUFFER, sticker_type)

        vf = ffmpeg_argv[0][ffmpeg_argv[0].index('-vf') + 1]
        assert vf == (
            'format=rgba,scale=512:512:force_original_aspect_ratio=increase:flags=bilinear,'
            f'fps=15,crop=512:512{shape},scale=512:512:flags=neighbor'
        )


class TestIsVideo:
    def test_mp4_detected(self) -> None:
        assert MediaFormat.is_video(b'\x00\x00\x00\x1cftypisom')

    def test_avi_detected(self) -> None:
        assert MediaFormat.is_video(b'RIFF\x00\x00\x00\x00AVI ')

    def test_mkv_detected(self) -> None:
        assert MediaFormat.is_video(b'\x1a\x45\xdf\xa3' + b'\x00' * 8)

    def test_png_not_video(self) -> None:
        assert not MediaFormat.is_video(_create_test_image())

    def test_short_buffer_not_video(self) -> None:
        assert not MediaFormat.is_video(b'\x00\x00')


class TestIsAnimatedWebp:
    def test_animated_webp_detected(self) -> None:
        assert MediaFormat.is_animated_webp(_create_animated_webp())

    def test_static_webp_not_detected(self) -> None:
        assert not MediaFormat.is_animated_webp(_create_static_webp())

    def test_png_not_detected(self) -> None:
        assert not MediaFormat.is_animated_webp(_create_test_image())

    def test_mp4_not_detected(self) -> None:
        assert not MediaFormat.is_animated_webp(b'\x00\x00\x00\x1cftypisom' + b'\x00' * 20)

    def test_short_buffer_not_detected(self) -> None:
        assert not MediaFormat.is_animated_webp(b'RIFF\x00\x00\x00\x00WEBP')


class TestStickerCreatorAnimatedWebp:
    @staticmethod
    def _open_webp(webp_bytes: bytes) -> Image.Image:
        return Image.open(io.BytesIO(webp_bytes))

    @pytest.mark.anyio
    async def test_animated_webp_preserves_animation(self) -> None:
        animated = _create_animated_webp(colors=('red', 'blue', 'green'))

        result = await StickerCreator.create(animated, 'full')

        img = self._open_webp(result)
        assert getattr(img, 'is_animated', False)
        assert getattr(img, 'n_frames', 0) == 3

    @pytest.mark.anyio
    async def test_animated_webp_resized_to_sticker_size(self) -> None:
        animated = _create_animated_webp(width=200, height=150)

        result = await StickerCreator.create(animated, 'full')

        img = self._open_webp(result)
        assert img.size == (512, 512)

    @pytest.mark.anyio
    async def test_animated_webp_skips_ffmpeg(self, mocker) -> None:
        mock_exec = mocker.patch(
            'asyncio.create_subprocess_exec',
        )

        await StickerCreator.create(_create_animated_webp(), 'full')

        mock_exec.assert_not_called()

    @pytest.mark.anyio
    async def test_static_webp_routes_to_image_path(self, mocker) -> None:
        mock_exec = mocker.patch(
            'asyncio.create_subprocess_exec',
        )

        result = await StickerCreator.create(_create_static_webp(), 'full')

        mock_exec.assert_not_called()
        img = self._open_webp(result)
        assert not getattr(img, 'is_animated', False)

    @pytest.mark.anyio
    async def test_animated_webp_quality_reduction_passed_to_pil(self, mocker) -> None:
        save_spy = mocker.spy(Image.Image, 'save')

        await StickerCreator.create(_create_animated_webp(), 'full', quality_reduction=50)

        assert save_spy.call_args.kwargs['quality'] == 25

    @pytest.mark.anyio
    async def test_animated_webp_quality_reduction_pixelates_frames(self) -> None:
        animated = _create_animated_webp(width=256, height=256)

        result = await StickerCreator.create(animated, 'full', quality_reduction=90)

        img = self._open_webp(result)
        assert img.size == STICKER_SIZE
        assert getattr(img, 'is_animated', False)

    @pytest.mark.anyio
    async def test_moderate_reduction_keeps_all_frames(self) -> None:
        eight_colors = ('red', 'blue', 'green', 'yellow', 'cyan', 'magenta', 'white', 'black')
        animated = _create_animated_webp(colors=eight_colors)

        result = await StickerCreator.create(animated, 'full', quality_reduction=50)

        img = self._open_webp(result)
        assert getattr(img, 'is_animated', False)
        assert getattr(img, 'n_frames', 0) == 8

    @pytest.mark.anyio
    async def test_heavy_reduction_shrinks_output(self) -> None:
        sixteen_colors = tuple(f'#{i * 16:02x}{255 - i * 16:02x}80' for i in range(16))
        animated = _create_animated_webp(width=512, height=512, colors=sixteen_colors)

        baseline = await StickerCreator.create(animated, 'full', quality_reduction=0)
        heavy = await StickerCreator.create(animated, 'full', quality_reduction=95)

        assert len(heavy) < len(baseline)

    @pytest.mark.anyio
    async def test_output_fits_animated_sticker_limit(self) -> None:
        from PIL import ImageDraw

        frames = []
        for i in range(40):
            img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            color = (255 - i * 6 % 256, i * 12 % 256, 128, 255)
            cx = 256 + int(80 * (i - 20) / 40)
            draw.ellipse((cx - 128, 128, cx + 128, 384), fill=color)
            frames.append(img)
        buf = io.BytesIO()
        frames[0].save(
            buf,
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=80,
            loop=0,
            quality=80,
        )

        heavy = await StickerCreator.create(buf.getvalue(), 'full', quality_reduction=99)

        assert len(heavy) <= MAX_ANIMATED_STICKER_BYTES

    @pytest.mark.anyio
    async def test_output_over_the_limit_at_every_stride_is_returned(self) -> None:
        noisy = _create_noise_webp(n_frames=4)

        result = await StickerCreator.create(noisy, 'full')

        assert len(result) > MAX_ANIMATED_STICKER_BYTES
        assert getattr(self._open_webp(result), 'n_frames', 0) == 2

    def test_parse_webp_durations_pads_a_truncated_anmf_chunk(self) -> None:
        truncated = (
            b'RIFF\x00\x00\x00\x00WEBP' + b'ANMF' + (100).to_bytes(4, 'little') + b'\x00' * 4
        )

        durations = MediaFormat.frame_durations(truncated, n_frames=2)

        assert durations == [MediaFormat.DEFAULT_FRAME_DURATION_MS] * 2

    def test_parse_webp_durations_reads_anmf_chunks(self) -> None:
        frames = [Image.new('RGBA', (64, 64), c) for c in ('red', 'blue', 'green', 'yellow')]
        buf = io.BytesIO()
        frames[0].save(
            buf,
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=[40, 60, 80, 120],
            loop=0,
        )

        durations = MediaFormat.frame_durations(buf.getvalue(), n_frames=4)

        assert durations == [40, 60, 80, 120]

    def test_parse_webp_durations_substitutes_default_for_zero(self) -> None:
        frames = [Image.new('RGBA', (64, 64), c) for c in ('red', 'blue')]
        buf = io.BytesIO()
        frames[0].save(
            buf,
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=0,
            loop=0,
        )

        durations = MediaFormat.frame_durations(buf.getvalue(), n_frames=2)

        assert all(d == MediaFormat.DEFAULT_FRAME_DURATION_MS for d in durations)


class TestOffTheEventLoop:
    @pytest.mark.anyio
    async def test_image_sticker_is_encoded_in_a_worker_thread(self, pillow_threads):
        await StickerCreator.create(_create_test_image())

        assert pillow_threads
        assert not any(pillow_threads)

    @pytest.mark.anyio
    async def test_animated_sticker_is_encoded_in_a_worker_thread(self, pillow_threads):
        await StickerCreator.create(_create_animated_webp())

        assert pillow_threads
        assert not any(pillow_threads)
