"""Render a top-down football pitch with player photos at formation positions."""

import io
import unicodedata
from dataclasses import dataclass
from typing import cast

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from bot.data.football_formations import Formation

_CANVAS_W = 640
_CANVAS_H = 960
_FIELD_COLOR = '#2e7d32'
_LINE_COLOR = '#ffffff'
_LINE_WIDTH = 3
_PHOTO_DIAMETER = 72
_FONT_SIZE = 15
_FONT_LABEL_SIZE = 22
_FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
_FONT_BOLD_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
_NAME_MAX_LEN = 14
_FLAG_W = 18
_FLAG_H = 12
_FLAG_GAP = 3
_STROKE_WIDTH = 2

# Field margin inside canvas (pixels)
_MX = 36
_MY = 60
_FW = _CANVAS_W - 2 * _MX
_FH = _CANVAS_H - 2 * _MY

_PENALTY_W_RATIO = 0.62
_PENALTY_H_RATIO = 0.18
_GOAL_W_RATIO = 0.24
_GOAL_H_RATIO = 0.05
_CIRCLE_R_RATIO = 0.10
_SPOT_R = 4
_PENALTY_SPOT_Y_RATIO = 0.12
_CORNER_ARC_R = 20


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
                mask = Image.new('L', (_PHOTO_DIAMETER, _PHOTO_DIAMETER), 0)
                ImageDraw.Draw(mask).ellipse([0, 0, _PHOTO_DIAMETER, _PHOTO_DIAMETER], fill=255)
                self.canvas.paste(photo.convert('RGB'), (cx - r, cy - r), mask)
            except (OSError, ValueError):
                self._draw_placeholder(cx, cy, r)
        else:
            self._draw_placeholder(cx, cy, r)

        short_name = _shorten_name(name)
        bbox = self.draw.textbbox((0, 0), short_name, font=self.font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        label_y = cy + r + 6

        # Layout: [flag] [name], centered around cx
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
            width=2,
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
        cx = int(_MX + slot.x * _FW)
        cy = int(_MY + slot.y * _FH)
        renderer.draw_player(photo_bytes, name, cx, cy, flag_bytes)

    output = io.BytesIO()
    canvas.save(output, format='JPEG', quality=88)
    return output.getvalue()


def _draw_field(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle([_MX, _MY, _MX + _FW, _MY + _FH], outline=_LINE_COLOR, width=_LINE_WIDTH)

    mid_y = _MY + _FH // 2
    draw.line([(_MX, mid_y), (_MX + _FW, mid_y)], fill=_LINE_COLOR, width=_LINE_WIDTH)

    circle_r = int(_FH * _CIRCLE_R_RATIO)
    ccx, ccy = _MX + _FW // 2, mid_y
    draw.ellipse(
        [ccx - circle_r, ccy - circle_r, ccx + circle_r, ccy + circle_r],
        outline=_LINE_COLOR,
        width=_LINE_WIDTH,
    )
    draw.ellipse([ccx - _SPOT_R, ccy - _SPOT_R, ccx + _SPOT_R, ccy + _SPOT_R], fill=_LINE_COLOR)

    pen_w = int(_FW * _PENALTY_W_RATIO)
    pen_h = int(_FH * _PENALTY_H_RATIO)
    pen_x = _MX + (_FW - pen_w) // 2

    draw.rectangle([pen_x, _MY, pen_x + pen_w, _MY + pen_h], outline=_LINE_COLOR, width=_LINE_WIDTH)
    draw.rectangle(
        [pen_x, _MY + _FH - pen_h, pen_x + pen_w, _MY + _FH],
        outline=_LINE_COLOR,
        width=_LINE_WIDTH,
    )

    goal_w = int(_FW * _GOAL_W_RATIO)
    goal_h = int(_FH * _GOAL_H_RATIO)
    goal_x = _MX + (_FW - goal_w) // 2

    draw.rectangle(
        [goal_x, _MY, goal_x + goal_w, _MY + goal_h], outline=_LINE_COLOR, width=_LINE_WIDTH
    )
    draw.rectangle(
        [goal_x, _MY + _FH - goal_h, goal_x + goal_w, _MY + _FH],
        outline=_LINE_COLOR,
        width=_LINE_WIDTH,
    )

    # GK-side penalty spot only (bottom)
    spot_offset = int(_FH * _PENALTY_SPOT_Y_RATIO)
    fcx = _MX + _FW // 2
    spot_y = _MY + _FH - spot_offset
    draw.ellipse(
        [fcx - _SPOT_R, spot_y - _SPOT_R, fcx + _SPOT_R, spot_y + _SPOT_R],
        fill=_LINE_COLOR,
    )

    ar = _CORNER_ARC_R
    corners = [
        (_MX - ar, _MY - ar, 0, 90),
        (_MX + _FW - ar, _MY - ar, 90, 180),
        (_MX - ar, _MY + _FH - ar, 270, 360),
        (_MX + _FW - ar, _MY + _FH - ar, 180, 270),
    ]
    for bx, by, start, end in corners:
        draw.arc(
            [bx, by, bx + ar * 2, by + ar * 2],
            start=start,
            end=end,
            fill=_LINE_COLOR,
            width=_LINE_WIDTH,
        )


def _draw_formation_label(draw: ImageDraw.ImageDraw, formation_name: str) -> None:
    font = _load_font(_FONT_BOLD_PATH, _FONT_LABEL_SIZE)
    bbox = draw.textbbox((0, 0), formation_name, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((_CANVAS_W - tw) // 2, 14),
        formation_name,
        fill=_LINE_COLOR,
        font=font,
        stroke_width=_STROKE_WIDTH,
        stroke_fill='#000000',
    )


def _shorten_name(name: str) -> str:
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
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
