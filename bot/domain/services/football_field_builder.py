"""Render a top-down football pitch with player photos at formation positions."""

import io
import math
import unicodedata
from dataclasses import dataclass
from typing import cast

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from bot.data.football_formations import Formation

_CANVAS_W = 2000
_CANVAS_H = 2750
_FIELD_COLOR = '#2e7d32'
_STRIPE_DARK = '#296e2c'
_STRIPE_LIGHT = '#327836'
_LINE_COLOR = '#ffffff'
_LINE_WIDTH = 12
_PHOTO_DIAMETER = 275
_FONT_SIZE = 48
_FONT_LABEL_SIZE = 69
_FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
_FONT_BOLD_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
_NAME_MAX_LEN = 14
_FLAG_W = 56
_FLAG_H = 38
_FLAG_GAP = 10
_STROKE_WIDTH = 6

_MX = 112
_MY = 175
_FW = _CANVAS_W - 2 * _MX
_FH = _CANVAS_H - 2 * _MY

# Each side of the field narrows by this fraction of FW at the attack end (y=0)
_TOP_TAPER = 0.08
_N_LAWN_STRIPES = 14

_PENALTY_W_RATIO = 0.62
_PENALTY_H_RATIO = 0.18
_GOAL_W_RATIO = 0.32
_GOAL_H_RATIO = 0.08
_CIRCLE_R_RATIO = 0.10
_SPOT_R = 12
_PENALTY_SPOT_Y_RATIO = 0.12
_CORNER_ARC_R = 88
_PENALTY_ARC_R_RATIO = 0.12


def _field_xy(x: float, y: float) -> tuple[int, int]:
    """Map field-relative coords [0..1, 0..1] to canvas pixels with perspective taper."""
    taper = _TOP_TAPER * (1.0 - y)
    left = _MX + taper * _FW
    width = _FW * (1.0 - 2.0 * taper)
    return int(left + x * width), int(_MY + y * _FH)


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return cast('ImageFont.FreeTypeFont', ImageFont.load_default(size=size))


@dataclass
class _Renderer:
    canvas: Image.Image
    draw: ImageDraw.ImageDraw
    font: ImageFont.FreeTypeFont

    def draw_player(
        self,
        photo_bytes: bytes | None,
        name: str,
        cx: int,
        cy: int,
        flag_bytes: bytes | None = None,
    ) -> None:
        r = _PHOTO_DIAMETER // 2
        if photo_bytes:
            try:
                photo = Image.open(io.BytesIO(photo_bytes)).convert('RGBA')
                photo = photo.resize((_PHOTO_DIAMETER, _PHOTO_DIAMETER), Resampling.LANCZOS)
                bg = Image.new('RGBA', (_PHOTO_DIAMETER, _PHOTO_DIAMETER), (255, 255, 255, 255))
                bg.paste(photo, mask=photo.split()[3])
                mask = Image.new('L', (_PHOTO_DIAMETER, _PHOTO_DIAMETER), 0)
                ImageDraw.Draw(mask).ellipse([0, 0, _PHOTO_DIAMETER, _PHOTO_DIAMETER], fill=255)
                self.canvas.paste(bg.convert('RGB'), (cx - r, cy - r), mask)
            except (OSError, ValueError):
                self._draw_placeholder(cx, cy, r)
        else:
            self._draw_placeholder(cx, cy, r)

        short_name = _shorten_name(name)
        bbox = self.draw.textbbox((0, 0), short_name, font=self.font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        label_y = cy + r + 6

        flag_w = _FLAG_W + _FLAG_GAP if flag_bytes else 0
        content_w = tw + flag_w
        text_x = cx - content_w // 2 + flag_w

        self.draw.text(
            (text_x, label_y),
            short_name,
            fill=_LINE_COLOR,
            font=self.font,
            stroke_width=_STROKE_WIDTH,
            stroke_fill='#000000',
        )

        if flag_bytes:
            try:
                flag_img = Image.open(io.BytesIO(flag_bytes)).convert('RGBA')
                flag_img = flag_img.resize((_FLAG_W, _FLAG_H), Resampling.LANCZOS)
                flag_x = int(cx - content_w // 2)
                flag_y = int(label_y + (th - _FLAG_H) // 2)
                self.canvas.paste(flag_img.convert('RGB'), (flag_x, flag_y), flag_img)
            except (OSError, ValueError):
                pass

    def _draw_placeholder(self, cx: int, cy: int, r: int) -> None:
        self.draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill='#1b5e20',
            outline=_LINE_COLOR,
            width=4,
        )


def build_football_field(
    photos: list[bytes | None],
    names: list[str],
    formation: Formation,
    flags: list[bytes | None] | None = None,
) -> bytes:
    canvas = Image.new('RGB', (_CANVAS_W, _CANVAS_H), _FIELD_COLOR)
    draw = ImageDraw.Draw(canvas)
    _draw_field(draw)
    _draw_formation_label(draw, formation.name)

    font = _load_font(_FONT_PATH, _FONT_SIZE)
    renderer = _Renderer(canvas=canvas, draw=draw, font=font)
    for i, slot in enumerate(formation.slots):
        photo_bytes = photos[i] if i < len(photos) else None
        name = names[i] if i < len(names) else ''
        flag_bytes = flags[i] if flags and i < len(flags) else None
        cx, cy = _field_xy(slot.x, slot.y)
        renderer.draw_player(photo_bytes, name, cx, cy, flag_bytes)

    output = io.BytesIO()
    canvas.save(output, format='JPEG', quality=92)
    return output.getvalue()


def _draw_field(draw: ImageDraw.ImageDraw) -> None:
    _draw_lawn_stripes(draw)
    _draw_field_lines(draw)


def _draw_lawn_stripes(draw: ImageDraw.ImageDraw) -> None:
    for i in range(_N_LAWN_STRIPES):
        y0 = i / _N_LAWN_STRIPES
        y1 = (i + 1) / _N_LAWN_STRIPES
        color = _STRIPE_DARK if i % 2 == 0 else _STRIPE_LIGHT
        draw.polygon(
            [_field_xy(0, y0), _field_xy(1, y0), _field_xy(1, y1), _field_xy(0, y1)],
            fill=color,
        )


def _draw_field_lines(draw: ImageDraw.ImageDraw) -> None:
    # Outer boundary (trapezoid)
    draw.polygon(
        [_field_xy(0, 0), _field_xy(1, 0), _field_xy(1, 1), _field_xy(0, 1)],
        outline=_LINE_COLOR,
        width=_LINE_WIDTH,
    )

    # Midfield line
    draw.line([_field_xy(0, 0.5), _field_xy(1, 0.5)], fill=_LINE_COLOR, width=_LINE_WIDTH)

    # Center circle — ellipse reflecting perspective compression at midfield
    ccx, ccy = _field_xy(0.5, 0.5)
    circle_r = int(_FH * _CIRCLE_R_RATIO)
    h_r = int(circle_r * (1.0 - _TOP_TAPER))
    draw.ellipse(
        [ccx - h_r, ccy - circle_r, ccx + h_r, ccy + circle_r],
        outline=_LINE_COLOR,
        width=_LINE_WIDTH,
    )
    draw.ellipse([ccx - _SPOT_R, ccy - _SPOT_R, ccx + _SPOT_R, ccy + _SPOT_R], fill=_LINE_COLOR)

    px0 = (1.0 - _PENALTY_W_RATIO) / 2.0
    px1 = 1.0 - px0
    ph = _PENALTY_H_RATIO
    gx0 = (1.0 - _GOAL_W_RATIO) / 2.0
    gx1 = 1.0 - gx0
    gh = _GOAL_H_RATIO

    # Penalty boxes
    for y0, y1 in ((0.0, ph), (1.0 - ph, 1.0)):
        draw.polygon(
            [_field_xy(px0, y0), _field_xy(px1, y0), _field_xy(px1, y1), _field_xy(px0, y1)],
            outline=_LINE_COLOR,
            width=_LINE_WIDTH,
        )

    # Goal areas
    for y0, y1 in ((0.0, gh), (1.0 - gh, 1.0)):
        draw.polygon(
            [_field_xy(gx0, y0), _field_xy(gx1, y0), _field_xy(gx1, y1), _field_xy(gx0, y1)],
            outline=_LINE_COLOR,
            width=_LINE_WIDTH,
        )

    # Penalty spots
    spot_top = _field_xy(0.5, _PENALTY_SPOT_Y_RATIO)
    spot_bot = _field_xy(0.5, 1.0 - _PENALTY_SPOT_Y_RATIO)
    for sx, sy in (spot_top, spot_bot):
        draw.ellipse([sx - _SPOT_R, sy - _SPOT_R, sx + _SPOT_R, sy + _SPOT_R], fill=_LINE_COLOR)

    # Corner arcs
    # Bottom corners: the arc's upward tip overshoots the tapered field boundary.
    # Clip to the angle where the arc ray intersects the taper line: tan(a) = +-FH/(taper*FW).
    ar = _CORNER_ARC_R
    k = _TOP_TAPER * _FW / _FH
    clip_bl = math.degrees(math.atan2(-1.0, k)) % 360  # bottom-left start (≈273°)
    clip_br = math.degrees(math.atan2(-1.0, -k)) % 360  # bottom-right end  (≈267°)
    for (cx_c, cy_c), start, end in [
        (_field_xy(0, 0), 0, 90),
        (_field_xy(1, 0), 90, 180),
        (_field_xy(0, 1), clip_bl, 360),
        (_field_xy(1, 1), 180, clip_br),
    ]:
        draw.arc(
            [cx_c - ar, cy_c - ar, cx_c + ar, cy_c + ar],
            start=start,
            end=end,
            fill=_LINE_COLOR,
            width=_LINE_WIDTH,
        )

    # Penalty arcs (D shapes)
    pen_arc_r = int(_FH * _PENALTY_ARC_R_RATIO)

    spot_bx, spot_by = spot_bot
    box_top_y = _field_xy(0.5, 1.0 - ph)[1]
    d_bot = spot_by - box_top_y
    if pen_arc_r > d_bot > 0:
        h_bot = math.sqrt(pen_arc_r**2 - d_bot**2)
        a1 = math.degrees(math.atan2(-d_bot, -h_bot)) % 360
        a2 = math.degrees(math.atan2(-d_bot, h_bot)) % 360
        draw.arc(
            [spot_bx - pen_arc_r, spot_by - pen_arc_r, spot_bx + pen_arc_r, spot_by + pen_arc_r],
            start=a1,
            end=a2,
            fill=_LINE_COLOR,
            width=_LINE_WIDTH,
        )

    spot_tx, spot_ty = spot_top
    box_bot_y = _field_xy(0.5, ph)[1]
    d_top = box_bot_y - spot_ty
    if pen_arc_r > d_top > 0:
        h_top = math.sqrt(pen_arc_r**2 - d_top**2)
        a1_top = math.degrees(math.atan2(d_top, h_top)) % 360
        a2_top = math.degrees(math.atan2(d_top, -h_top)) % 360
        draw.arc(
            [spot_tx - pen_arc_r, spot_ty - pen_arc_r, spot_tx + pen_arc_r, spot_ty + pen_arc_r],
            start=a1_top,
            end=a2_top,
            fill=_LINE_COLOR,
            width=_LINE_WIDTH,
        )


def _draw_formation_label(draw: ImageDraw.ImageDraw, formation_name: str) -> None:
    font = _load_font(_FONT_BOLD_PATH, _FONT_LABEL_SIZE)
    name = unicodedata.normalize('NFKD', formation_name).encode('ascii', 'ignore').decode('ascii')
    bbox = draw.textbbox((0, 0), name, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((_CANVAS_W - tw) // 2, _MY // 3),
        name,
        fill=_LINE_COLOR,
        font=font,
        stroke_width=_STROKE_WIDTH,
        stroke_fill='#000000',
    )


def _shorten_name(name: str) -> str:
    name = unicodedata.normalize('NFC', name)
    parts = name.split()
    if len(parts) <= 1:
        return name[:_NAME_MAX_LEN]
    last = parts[-1]
    if len(last) > _NAME_MAX_LEN:
        return last[:_NAME_MAX_LEN]
    abbreviated = f'{parts[0][0]}. {last}'
    if len(abbreviated) <= _NAME_MAX_LEN:
        return abbreviated
    return last
