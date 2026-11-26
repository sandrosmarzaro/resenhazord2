import io
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from bot.data.sticker import MAX_ANIMATED_STICKER_BYTES, MAX_STICKER_QUALITY, STICKER_SIZE
from bot.domain.exceptions import StickerTooLargeError
from bot.domain.services.sticker.frame_shaper import FrameShaper
from bot.domain.services.sticker.media_format import MediaFormat
from bot.domain.services.sticker.video_sticker_encoder import VideoStickerEncoder
from bot.domain.services.sticker_creator import StickerCreator

VIDEO_BUFFER = b'\x00\x00\x00\x1c' + b'ftyp' + b'isom' + b'\x00' * 100


def _probe_json(fps: str = '30/1', seconds: float = 1.0) -> bytes:
    return json.dumps(
        {'streams': [{'avg_frame_rate': fps}], 'format': {'duration': str(seconds)}}
    ).encode()


# Answers ffprobe with the clip, each sample encode with frame_bytes per frame, and the
# full encodes with the outputs in turn (the last one repeats).
@pytest.fixture
def fake_ffmpeg(mocker):
    def install(
        *outputs: bytes, fps: str = '30/1', seconds: float = 1.0, frame_bytes: int = 100
    ) -> list[tuple[str, ...]]:
        calls: list[tuple[str, ...]] = []
        full_outputs = list(outputs or (b'fits',))

        def output(argv: tuple[str, ...]) -> bytes:
            if 'libwebp' not in argv:
                return b'sample'
            if '-t' not in argv:
                return b'x' * frame_bytes * VideoStickerEncoder.SAMPLE_FRAMES
            return full_outputs.pop(0) if len(full_outputs) > 1 else full_outputs[0]

        def fake_exec(*argv, **_kwargs):
            calls.append(argv)
            proc = mocker.AsyncMock()
            proc.returncode = 0
            stdout = _probe_json(fps, seconds) if argv[0] == 'ffprobe' else b''
            proc.communicate.return_value = (stdout, b'')
            if argv[0] == 'ffmpeg':
                Path(argv[-1]).write_bytes(output(argv))
            return proc

        mocker.patch('asyncio.create_subprocess_exec', side_effect=fake_exec)
        return calls

    return install


def _encodes(calls: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    return [argv for argv in calls if 'libwebp' in argv and '-t' in argv]


def _arg(argv: tuple[str, ...], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _fps(argv: tuple[str, ...]) -> str:
    return _arg(argv, '-vf').split(',')[0]


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


# Flat colours encode to the same bytes at any quality; detail doesn't.
def _create_detailed_static_webp() -> bytes:
    img = Image.effect_mandelbrot(STICKER_SIZE, (-2, -1.5, 1, 1.5), 100).convert('RGBA')
    buf = io.BytesIO()
    img.save(buf, format='WEBP', quality=90)
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
    async def test_quality_reduction_caps_the_video_quality(self, fake_ffmpeg) -> None:
        calls = fake_ffmpeg()

        await StickerCreator.create(VIDEO_BUFFER, 'full', quality_reduction=80)

        assert _arg(_encodes(calls)[0], '-quality') == '19'

    @pytest.mark.anyio
    async def test_probe_error_propagates(self, mock_subprocess) -> None:
        mock_subprocess('asyncio.create_subprocess_exec', calls=[(b'', b'invalid data', 1)])

        with pytest.raises(RuntimeError, match='ffprobe failed: invalid data'):
            await StickerCreator.create(VIDEO_BUFFER, 'full')

    @pytest.mark.anyio
    async def test_ffmpeg_error_propagates(self, mock_subprocess) -> None:
        mock_subprocess(
            'asyncio.create_subprocess_exec',
            calls=[(_probe_json(), b'', 0), (b'', b'conversion failed', 1)],
        )

        with pytest.raises(RuntimeError, match='ffmpeg failed: conversion failed'):
            await StickerCreator.create(VIDEO_BUFFER, 'full')


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

    @pytest.mark.anyio
    async def test_keeps_every_frame_of_a_short_clip(self, landscape_video) -> None:
        result = await StickerCreator.create(landscape_video, 'full')

        assert Image.open(io.BytesIO(result)).n_frames == 15


class TestVideoFfmpegCommand:
    # fps first: the frames it drops are never converted or scaled.
    FULL_FILTER = (
        'fps=30,format=rgba,scale=512:512:force_original_aspect_ratio=decrease:flags=bilinear,'
        'pad=512:512:-1:-1:color=0x00000000,scale=512:512:flags=neighbor'
    )

    # Any member can hand over the video: a crafted one can be an hls or concat playlist
    # that makes ffmpeg fetch URLs or read local files.
    @pytest.mark.anyio
    async def test_opens_the_video_only_as_a_local_file(self, fake_ffmpeg) -> None:
        calls = fake_ffmpeg()

        await StickerCreator.create(VIDEO_BUFFER, 'full')

        readers = [argv for argv in calls if _arg(argv, '-i').endswith('/input')]
        assert [argv[0] for argv in readers] == ['ffprobe', 'ffmpeg', 'ffmpeg']
        assert {argv[argv.index('-i') - 4 : argv.index('-i')] for argv in readers} == {
            VideoStickerEncoder.INPUT_ARGS
        }

    # A second full encode writes over the first: without -y ffmpeg asks on stdin and
    # waits forever.
    @pytest.mark.anyio
    async def test_ffmpeg_never_asks_on_stdin(self, fake_ffmpeg) -> None:
        calls = fake_ffmpeg(b'x' * 300_000, b'fits', seconds=10, frame_bytes=2_000)

        await StickerCreator.create(VIDEO_BUFFER, 'full')

        ffmpeg_calls = [argv for argv in calls if argv[0] == 'ffmpeg']
        assert {argv[1:3] for argv in ffmpeg_calls} == {('-nostdin', '-y')}

    @pytest.mark.anyio
    async def test_full_video_runs_the_expected_ffmpeg_command(self, fake_ffmpeg) -> None:
        calls = fake_ffmpeg()

        await StickerCreator.create(VIDEO_BUFFER, 'full')

        argv = _encodes(calls)[0]
        assert argv[argv.index('-i') + 2 : -1] == (
            '-vcodec',
            'libwebp',
            '-vf',
            self.FULL_FILTER,
            '-quality',
            '95',
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
                (
                    ",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                    "a='255*lte(hypot(max(0,max(W/8-X-0.5,X+0.5-W+W/8)),"
                    "max(0,max(H/8-Y-0.5,Y+0.5-H+H/8))),W/8)'"
                ),
            ),
        ],
    )
    async def test_shaped_video_is_cropped_and_masked(
        self, fake_ffmpeg, sticker_type, shape
    ) -> None:
        calls = fake_ffmpeg()

        await StickerCreator.create(VIDEO_BUFFER, sticker_type)

        assert _arg(_encodes(calls)[0], '-vf') == (
            'fps=30,format=rgba,scale=512:512:force_original_aspect_ratio=increase:flags=bilinear,'
            f'crop=512:512{shape},scale=512:512:flags=neighbor'
        )

    @pytest.mark.anyio
    async def test_measures_frames_spread_over_the_whole_clip(self, fake_ffmpeg) -> None:
        calls = fake_ffmpeg(seconds=10)

        await StickerCreator.create(VIDEO_BUFFER, 'full')

        sample = next(argv for argv in calls if '-frames:v' in argv)
        assert (_fps(sample), _arg(sample, '-frames:v')) == ('fps=2', '20')

    @pytest.mark.anyio
    async def test_keeps_the_frame_rate_of_a_slow_source(self, fake_ffmpeg) -> None:
        calls = fake_ffmpeg(fps='15/1')

        await StickerCreator.create(VIDEO_BUFFER, 'full')

        assert _fps(_encodes(calls)[0]) == 'fps=15'

    @pytest.mark.anyio
    async def test_drops_frames_when_the_clip_does_not_fit_at_full_frame_rate(
        self, fake_ffmpeg
    ) -> None:
        # 300 frames of 2 kB are 600 kB; 240 of them fit.
        calls = fake_ffmpeg(seconds=10, frame_bytes=2_000)

        await StickerCreator.create(VIDEO_BUFFER, 'full')

        argv = _encodes(calls)[0]
        assert (_fps(argv), _arg(argv, '-quality')) == ('fps=24', '95')

    @pytest.mark.anyio
    async def test_oversized_video_is_planned_again_for_a_smaller_budget(self, fake_ffmpeg) -> None:
        # The sample says 300 frames x 1.6 kB = 480 kB, but the encode weighs 600 kB.
        calls = fake_ffmpeg(b'x' * 600_000, b'fits', seconds=10, frame_bytes=1_600)

        result = await StickerCreator.create(VIDEO_BUFFER, 'full')

        assert result == b'fits'
        assert [_fps(argv) for argv in _encodes(calls)] == ['fps=30', 'fps=24']

    @pytest.mark.anyio
    async def test_video_still_over_the_limit_after_planning_again_is_refused(
        self, fake_ffmpeg
    ) -> None:
        fake_ffmpeg(b'x' * MAX_ANIMATED_STICKER_BYTES * 2, seconds=10, frame_bytes=1_600)

        with pytest.raises(StickerTooLargeError):
            await StickerCreator.create(VIDEO_BUFFER, 'full')

    @pytest.mark.anyio
    async def test_video_that_fits_no_step_is_refused_before_a_full_encode(
        self, fake_ffmpeg
    ) -> None:
        calls = fake_ffmpeg(frame_bytes=MAX_ANIMATED_STICKER_BYTES)

        with pytest.raises(StickerTooLargeError):
            await StickerCreator.create(VIDEO_BUFFER, 'full')

        assert _encodes(calls) == []


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

        assert save_spy.call_args.kwargs['quality'] == 48

    # Pillow saves animations with method 0, whose sizes jump down at some qualities
    # (q89 halves the detail) and break the quality search.
    @pytest.mark.anyio
    async def test_animation_is_encoded_with_the_default_libwebp_effort(self, mocker) -> None:
        animated = _create_animated_webp()
        save_spy = mocker.spy(Image.Image, 'save')

        await StickerCreator.create(animated, 'full')

        assert {call.kwargs['method'] for call in save_spy.call_args_list} == {4}

    @pytest.mark.anyio
    async def test_short_animation_keeps_the_highest_quality(self, mocker) -> None:
        save_spy = mocker.spy(Image.Image, 'save')

        await StickerCreator.create(_create_animated_webp(), 'full')

        assert save_spy.call_args.kwargs['quality'] == MAX_STICKER_QUALITY

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
    async def test_heavy_animation_drops_frames_and_keeps_its_length(self) -> None:
        frames = [
            Image.frombytes('RGB', (96, 96), os.urandom(96 * 96 * 3)).convert('RGBA')
            for _ in range(30)
        ]
        buf = io.BytesIO()
        frames[0].save(
            buf, format='WEBP', save_all=True, append_images=frames[1:], duration=50, quality=90
        )

        result = await StickerCreator.create(buf.getvalue(), 'full')

        n_frames = Image.open(io.BytesIO(result)).n_frames
        assert len(result) <= MAX_ANIMATED_STICKER_BYTES
        assert n_frames < len(frames)
        assert sum(MediaFormat.frame_durations(result, n_frames)) == 50 * len(frames)

    @pytest.mark.anyio
    async def test_output_over_the_limit_at_every_frame_rate_is_refused(self) -> None:
        noisy = _create_noise_webp(n_frames=4)

        with pytest.raises(StickerTooLargeError, match='500 KB'):
            await StickerCreator.create(noisy, 'full')

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


class TestWholeStickerReuse:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'sticker',
        [_create_animated_webp(512, 512), _create_detailed_static_webp()],
        ids=['animated', 'static'],
    )
    async def test_full_keeps_the_bytes_of_a_whole_sticker(self, sticker) -> None:
        result = await StickerCreator.create(sticker, 'full')

        assert result == sticker

    @pytest.mark.anyio
    async def test_a_shape_encodes_the_sticker_again(self) -> None:
        sticker = _create_animated_webp(512, 512)

        result = await StickerCreator.create(sticker, 'circle')

        assert result != sticker

    @pytest.mark.anyio
    async def test_a_quality_reduction_encodes_the_sticker_again(self) -> None:
        sticker = _create_animated_webp(512, 512)

        result = await StickerCreator.create(sticker, 'full', quality_reduction=50)

        assert result != sticker

    @pytest.mark.anyio
    async def test_a_sticker_over_the_limit_is_encoded_again(self) -> None:
        noise = Image.frombytes('RGBA', STICKER_SIZE, os.urandom(512 * 512 * 4))
        buf = io.BytesIO()
        noise.save(buf, format='WEBP', lossless=True)
        sticker = buf.getvalue()

        result = await StickerCreator.create(sticker, 'full')

        assert len(sticker) > MAX_ANIMATED_STICKER_BYTES
        assert result != sticker

    @pytest.mark.anyio
    async def test_a_whole_sized_image_that_is_not_webp_is_encoded(self) -> None:
        image = _create_test_image(512, 512)

        result = await StickerCreator.create(image, 'full')

        assert Image.open(io.BytesIO(result)).format == 'WEBP'


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
