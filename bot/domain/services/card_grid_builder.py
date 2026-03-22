"""Build a card grid image from individual card image buffers using Pillow."""

import io

from PIL import Image
from PIL.Image import Resampling


def build_card_grid(
    image_buffers: list[bytes],
    *,
    columns: int = 3,
    cell_width: int = 300,
    cell_height: int = 420,
) -> bytes:
    """Arrange card images into a grid and return the result as PNG bytes."""
    rows = (len(image_buffers) + columns - 1) // columns
    grid = Image.new('RGBA', (columns * cell_width, rows * cell_height), (0, 0, 0, 0))

    for i, buf in enumerate(image_buffers):
        card = Image.open(io.BytesIO(buf)).convert('RGBA')
        card.thumbnail((cell_width, cell_height), Resampling.LANCZOS)

        x = (i % columns) * cell_width + (cell_width - card.width) // 2
        y = (i // columns) * cell_height + (cell_height - card.height) // 2
        grid.paste(card, (x, y), card)

    output = io.BytesIO()
    grid.save(output, format='PNG')
    return output.getvalue()
