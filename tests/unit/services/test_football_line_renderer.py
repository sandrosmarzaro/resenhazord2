import math

import pytest
from PIL import Image, ImageDraw

from bot.domain.services.football_field.field_config import DEFAULT_CONFIG, field_xy
from bot.domain.services.football_field.line_renderer import LineRenderer

_WHITE = (255, 255, 255)
_ARC_SAMPLE_DEGREES = 45


def _render_lines() -> Image.Image:
    canvas = DEFAULT_CONFIG.canvas
    image = Image.new('RGB', (canvas.width, canvas.height), (0, 0, 0))
    LineRenderer(ImageDraw.Draw(image), DEFAULT_CONFIG).render()
    return image


def _arc_point(spot_y_ratio: float, towards_midfield: int, *, outward: bool) -> tuple[int, int]:
    spot_x, spot_y = field_xy(0.5, spot_y_ratio, DEFAULT_CONFIG)
    radius = DEFAULT_CONFIG.fh * DEFAULT_CONFIG.draw.penalty_arc_r_ratio
    angle = math.radians(_ARC_SAMPLE_DEGREES)
    direction = towards_midfield if outward else -towards_midfield
    return (
        int(spot_x + radius * math.sin(angle)),
        int(spot_y + direction * radius * math.cos(angle)),
    )


_SPOT_RATIO = DEFAULT_CONFIG.draw.penalty_spot_y_ratio
_BOXES = [
    pytest.param(_SPOT_RATIO, 1, id='top'),
    pytest.param(1.0 - _SPOT_RATIO, -1, id='bottom'),
]


class TestPenaltyArc:
    @pytest.mark.parametrize(('spot_y_ratio', 'towards_midfield'), _BOXES)
    def test_draws_arc_outside_the_box(self, spot_y_ratio, towards_midfield):
        image = _render_lines()

        pixel = image.getpixel(_arc_point(spot_y_ratio, towards_midfield, outward=True))

        assert pixel == _WHITE

    @pytest.mark.parametrize(('spot_y_ratio', 'towards_midfield'), _BOXES)
    def test_leaves_inside_of_the_box_clear(self, spot_y_ratio, towards_midfield):
        image = _render_lines()

        pixel = image.getpixel(_arc_point(spot_y_ratio, towards_midfield, outward=False))

        assert pixel != _WHITE
