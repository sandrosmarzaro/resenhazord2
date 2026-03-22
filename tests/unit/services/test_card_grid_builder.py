import io

from PIL import Image

from bot.domain.services.card_grid_builder import build_card_grid


def _make_card_image(width: int = 200, height: int = 300, color: str = 'red') -> bytes:
    img = Image.new('RGBA', (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class TestBuildCardGrid:
    def test_returns_png_bytes(self):
        buffers = [_make_card_image() for _ in range(6)]

        result = build_card_grid(buffers)

        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.format == 'PNG'

    def test_default_grid_dimensions(self):
        buffers = [_make_card_image() for _ in range(6)]

        result = build_card_grid(buffers)

        img = Image.open(io.BytesIO(result))
        assert img.size == (900, 840)  # 3 columns * 300, 2 rows * 420

    def test_custom_grid_dimensions(self):
        buffers = [_make_card_image() for _ in range(4)]

        result = build_card_grid(buffers, columns=2, cell_width=200, cell_height=300)

        img = Image.open(io.BytesIO(result))
        assert img.size == (400, 600)  # 2 columns * 200, 2 rows * 300

    def test_single_card(self):
        buffers = [_make_card_image()]

        result = build_card_grid(buffers, columns=3)

        img = Image.open(io.BytesIO(result))
        assert img.size == (900, 420)  # 3 columns * 300, 1 row * 420

    def test_handles_different_card_sizes(self):
        buffers = [
            _make_card_image(100, 150, 'red'),
            _make_card_image(250, 400, 'blue'),
            _make_card_image(300, 420, 'green'),
        ]

        result = build_card_grid(buffers, columns=3)

        img = Image.open(io.BytesIO(result))
        assert img.size == (900, 420)
