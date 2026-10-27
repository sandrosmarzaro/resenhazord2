import io

import pytest
from PIL import Image

from bot.data.football_formations import FORMATIONS
from bot.domain.services.football_field.build_field import build_card_field, build_football_field
from bot.domain.services.football_field.field_config import field_xy
from bot.domain.services.football_field.player_renderer import shorten_name

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


def _card(color: tuple[int, int, int, int]) -> bytes:
    output = io.BytesIO()
    Image.new('RGBA', (680, 895), color).save(output, format='PNG')
    return output.getvalue()


class TestBuildCardField:
    def test_pastes_each_card_on_its_slot(self):
        result = build_card_field([_card((200, 160, 40, 255))] * _N, _FORMATION, 'OVR médio 90')

        img = Image.open(io.BytesIO(result)).convert('RGB')
        slot = _FORMATION.slots[0]
        red, green, blue = img.getpixel(field_xy(slot.x, slot.y))
        assert max(abs(red - 200), abs(green - 160), abs(blue - 40)) < 8

    def test_keeps_the_lawn_under_transparent_corners(self):
        cards = [_card((0, 0, 0, 0))] * _N

        result = build_card_field(cards, _FORMATION, None)

        img = Image.open(io.BytesIO(result)).convert('RGB')
        slot = _FORMATION.slots[0]
        red, green, _ = img.getpixel(field_xy(slot.x, slot.y))
        assert green > red

    def test_missing_cards_leave_a_placeholder(self):
        result = build_card_field([None] * _N, _FORMATION, None)

        assert Image.open(io.BytesIO(result)).size == (2000, 2750)


class TestShortenName:
    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('Messi', 'Messi'),
            ('Lionel Messi', 'L. Messi'),
            ('Cristiano Ronaldo', 'C. Ronaldo'),
            ('Vinicius Junior', 'V. Junior'),
            ('Vinícius Jr.', 'Vinícius Jr.'),
            ('Virgil van Dijk', 'V. van Dijk'),
            ('Kevin De Bruyne', 'K. De Bruyne'),
            ('Neymar da Silva Santos Júnior', 'Santos Júnior'),
            ('Pelé', 'Pelé'),
            ('', ''),
            ('VeryLongSingleNameThatExceedsLimit', 'VeryLongSingl'),
            ('A VeryLongLastNameThatExceedsLimit', 'VeryLongLastN'),
        ],
    )
    def testshorten_name(self, name, expected):
        assert shorten_name(name) == expected


class TestFieldXy:
    def test_center_maps_to_canvas_center(self):
        cx, cy = field_xy(0.5, 0.5)

        assert cx == 1000
        assert cy == 1375

    def test_top_left_has_taper_offset(self):
        cx, cy = field_xy(0, 0)

        assert cx > 112
        assert cy == 175

    def test_bottom_right_reaches_far_edge(self):
        cx, cy = field_xy(1, 1)

        assert cx == 1888
        assert cy == 2575

    def test_y_zero_is_top_of_field(self):
        _, cy = field_xy(0.5, 0)

        assert cy == 175

    def test_y_one_is_bottom_of_field(self):
        _, cy = field_xy(0.5, 1)

        assert cy == 2575
