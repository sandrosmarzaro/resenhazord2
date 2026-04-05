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
