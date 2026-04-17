import io
from pathlib import Path

import pytest
from PIL import Image

from bot.domain.services.sticker_creator import StickerCreator


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
        img = Image.new('RGBA', StickerCreator.STICKER_SIZE, 'red')
        for x in range(img.width):
            for y in range(img.height):
                img.putpixel((x, y), (x % 256, y % 256, 128, 255))

        result = StickerCreator._pixelate(img, working_size=32)

        assert result.size == StickerCreator.STICKER_SIZE
        block = StickerCreator.STICKER_SIZE[0] // 32
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
        assert StickerCreator._effective_working_size(0) == StickerCreator.STICKER_SIZE[0]

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

        async def fake_exec(*args, **_kwargs):
            write_fake_output(*args)
            return mock_proc

        mock_exec = mocker.patch(
            'bot.domain.services.sticker_creator.asyncio.create_subprocess_exec',
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

        async def fake_run(*args, **_kwargs):
            write_fake_output(*args)
            return mock_proc

        mock_run = mocker.patch(
            'bot.domain.services.sticker_creator.asyncio.create_subprocess_exec',
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
            'bot.domain.services.sticker_creator.asyncio.create_subprocess_exec',
            return_value=mock_proc,
        )
        video_buffer = b'\x00\x00\x00\x1c' + b'ftyp' + b'isom' + b'\x00' * 100

        with pytest.raises(RuntimeError, match='ffmpeg failed'):
            await StickerCreator.create(video_buffer, 'full')


class TestIsVideo:
    def test_mp4_detected(self) -> None:
        assert StickerCreator._is_video(b'\x00\x00\x00\x1cftypisom')

    def test_avi_detected(self) -> None:
        assert StickerCreator._is_video(b'RIFF\x00\x00\x00\x00AVI ')

    def test_mkv_detected(self) -> None:
        assert StickerCreator._is_video(b'\x1a\x45\xdf\xa3' + b'\x00' * 8)

    def test_png_not_video(self) -> None:
        assert not StickerCreator._is_video(_create_test_image())

    def test_short_buffer_not_video(self) -> None:
        assert not StickerCreator._is_video(b'\x00\x00')


class TestIsAnimatedWebp:
    def test_animated_webp_detected(self) -> None:
        assert StickerCreator._is_animated_webp(_create_animated_webp())

    def test_static_webp_not_detected(self) -> None:
        assert not StickerCreator._is_animated_webp(_create_static_webp())

    def test_png_not_detected(self) -> None:
        assert not StickerCreator._is_animated_webp(_create_test_image())

    def test_mp4_not_detected(self) -> None:
        assert not StickerCreator._is_animated_webp(b'\x00\x00\x00\x1cftypisom' + b'\x00' * 20)

    def test_short_buffer_not_detected(self) -> None:
        assert not StickerCreator._is_animated_webp(b'RIFF\x00\x00\x00\x00WEBP')


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
            'bot.domain.services.sticker_creator.asyncio.create_subprocess_exec',
        )

        await StickerCreator.create(_create_animated_webp(), 'full')

        mock_exec.assert_not_called()

    @pytest.mark.anyio
    async def test_static_webp_routes_to_image_path(self, mocker) -> None:
        mock_exec = mocker.patch(
            'bot.domain.services.sticker_creator.asyncio.create_subprocess_exec',
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
        assert img.size == StickerCreator.STICKER_SIZE
        assert getattr(img, 'is_animated', False)

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

        durations = StickerCreator._parse_webp_durations(buf.getvalue(), n_frames=4)

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

        durations = StickerCreator._parse_webp_durations(buf.getvalue(), n_frames=2)

        assert all(d == StickerCreator.DEFAULT_FRAME_DURATION_MS for d in durations)
