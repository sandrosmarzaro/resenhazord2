import io

import pytest
from PIL import Image

from bot.data.football_formations import FORMATIONS
from bot.domain.services.football_field_builder import (
    _field_xy,
    _shorten_name,
    build_football_field,
)

_FORMATION = FORMATIONS[0]
_N = len(_FORMATION.slots)


class TestBuildFootballField:
    def test_returns_jpeg_bytes(self):
        result = build_football_field([None] * _N, [''] * _N, _FORMATION)

        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.format == 'JPEG'

    def test_canvas_dimensions(self):
        result = build_football_field([None] * _N, [''] * _N, _FORMATION)

        img = Image.open(io.BytesIO(result))
        assert img.size == (2000, 2750)

    def test_accepts_none_photos(self):
        result = build_football_field([None] * _N, ['Player'] * _N, _FORMATION)

        assert len(result) > 0

    def test_accepts_overlays(self):
        overlays: list[tuple[str | None, bytes | None]] = [(None, None)] * _N

        result = build_football_field([None] * _N, [''] * _N, _FORMATION, overlays=overlays)

        assert isinstance(result, bytes)

    def test_accepts_total_value(self):
        result = build_football_field(
            [None] * _N, [''] * _N, _FORMATION, total_value='€ 1.200,00 mi.'
        )

        assert isinstance(result, bytes)

    def test_fewer_photos_than_slots(self):
        result = build_football_field([], [], _FORMATION)

        assert isinstance(result, bytes)


class TestShortenName:
    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('Messi', 'Messi'),
            ('Lionel Messi', 'L. Messi'),
            ('Cristiano Ronaldo', 'C. Ronaldo'),
            ('Vinicius Junior', 'V. Junior'),
            ('Pelé', 'Pelé'),
            ('', ''),
            ('VeryLongSingleNameThatExceedsLimit', 'VeryLongSingl'),
            ('A VeryLongLastNameThatExceedsLimit', 'VeryLongLastN'),
        ],
    )
    def test_shorten_name(self, name, expected):
        assert _shorten_name(name) == expected


class TestFieldXy:
    def test_center_maps_to_canvas_center(self):
        cx, cy = _field_xy(0.5, 0.5)

        assert cx == 1000
        assert cy == 1375

    def test_top_left_has_taper_offset(self):
        cx, cy = _field_xy(0, 0)

        assert cx > 112
        assert cy == 175

    def test_bottom_right_reaches_far_edge(self):
        cx, cy = _field_xy(1, 1)

        assert cx == 1888
        assert cy == 2575

    def test_y_zero_is_top_of_field(self):
        _, cy = _field_xy(0.5, 0)

        assert cy == 175

    def test_y_one_is_bottom_of_field(self):
        _, cy = _field_xy(0.5, 1)

        assert cy == 2575
