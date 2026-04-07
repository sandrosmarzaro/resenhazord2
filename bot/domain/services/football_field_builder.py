"""Render a top-down football pitch with player photos at formation positions."""

import contextlib
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
_CANVAS_BG = '#000000'
_FIELD_COLOR = '#2e7d32'
_STRIPE_DARK = '#296e2c'
_STRIPE_LIGHT = '#327836'
_LINE_COLOR = '#ffffff'
_LINE_WIDTH = 12
_PHOTO_DIAMETER = 250
_BADGE_SIZE = int(_PHOTO_DIAMETER * 0.42)  # badge longest side
_FLAG_SIZE = int(_PHOTO_DIAMETER * 0.36)  # flag longest side
_OVERLAY_CY_RATIO = 0.62  # vertical center of overlay relative to photo radius (below photo center)
_OVERLAY_OFFSET_X_RATIO = 0.78
_FONT_SIZE = 40
_FONT_LABEL_SIZE = 69
_EMOJI_NATIVE_SIZE = 109  # NotoColorEmoji bitmap strike size
_FONT_PATHS = [
    '/usr/share/fonts/dejavu/DejaVuSans.ttf',  # Alpine
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Ubuntu/Debian
]
_FONT_BOLD_PATHS = [
    '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]
_EMOJI_FONT_PATHS = [
    '/usr/share/fonts/noto/NotoColorEmoji.ttf',  # Alpine
    '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',  # Ubuntu/Debian
]
_NAME_MAX_LEN = 13
_STROKE_WIDTH = 5

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


def _load_font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in paths:
        with contextlib.suppress(OSError):
            return ImageFont.truetype(path, size)
    return cast('ImageFont.FreeTypeFont', ImageFont.load_default(size=size))


def _load_font_optional(paths: list[str], size: int) -> ImageFont.FreeTypeFont | None:
    for path in paths:
        with contextlib.suppress(OSError):
            return ImageFont.truetype(path, size)
    return None


@dataclass
class _Renderer:
    canvas: Image.Image
    draw: ImageDraw.ImageDraw
    font: ImageFont.FreeTypeFont

    emoji_font: ImageFont.FreeTypeFont | None = None

    def draw_player(
        self,
        photo_bytes: bytes | None,
        name: str,
        cx: int,
        cy: int,
        overlays: tuple[str | None, bytes | None] | None = None,
    ) -> None:
        r = _PHOTO_DIAMETER // 2
        if photo_bytes:
            with contextlib.suppress(OSError, ValueError):
                photo = Image.open(io.BytesIO(photo_bytes)).convert('RGBA')
                photo = photo.resize((_PHOTO_DIAMETER, _PHOTO_DIAMETER), Resampling.LANCZOS)
                bg = Image.new('RGBA', (_PHOTO_DIAMETER, _PHOTO_DIAMETER), (255, 255, 255, 255))
                bg.paste(photo, mask=photo.split()[3])
                mask = Image.new('L', (_PHOTO_DIAMETER, _PHOTO_DIAMETER), 0)
                ImageDraw.Draw(mask).ellipse([0, 0, _PHOTO_DIAMETER, _PHOTO_DIAMETER], fill=255)
                self.canvas.paste(bg.convert('RGB'), (cx - r, cy - r), mask)
        else:
            self._draw_placeholder(cx, cy, r)

        # Overlay flag at bottom-left, badge at bottom-right; centers below photo midline
        if overlays:
            ov_cy = cy + int(r * _OVERLAY_CY_RATIO)
            ov_offset_x = int(r * _OVERLAY_OFFSET_X_RATIO)
            flag_emoji, badge_image = overlays
            if flag_emoji:
                self._draw_flag_emoji(flag_emoji, cx - ov_offset_x, ov_cy)
            if badge_image:
                self._draw_badge(badge_image, cx + ov_offset_x, ov_cy)

        short_name = _shorten_name(name)
        bbox = self.draw.textbbox((0, 0), short_name, font=self.font)
        tw = bbox[2] - bbox[0]
        label_y = cy + r + 6
        self.draw.text(
            (cx - tw // 2, label_y),
            short_name,
            fill=_LINE_COLOR,
            font=self.font,
            stroke_width=_STROKE_WIDTH,
            stroke_fill='#000000',
        )

    def _draw_badge(self, img_bytes: bytes, cx: int, cy: int) -> None:
        with contextlib.suppress(Exception):
            img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
            ratio = min(_BADGE_SIZE / img.width, _BADGE_SIZE / img.height)
            new_w = max(1, int(img.width * ratio))
            new_h = max(1, int(img.height * ratio))
            img = img.resize((new_w, new_h), Resampling.LANCZOS)
            paste_x = cx - new_w // 2
            paste_y = cy - new_h // 2
            self.canvas.paste(img.convert('RGB'), (paste_x, paste_y), img.split()[3])

    def _draw_flag_emoji(self, emoji: str, cx: int, cy: int) -> None:
        if not self.emoji_font:
            return
        with contextlib.suppress(Exception):
            tmp = Image.new('RGBA', (_EMOJI_NATIVE_SIZE * 2, _EMOJI_NATIVE_SIZE * 2), (0, 0, 0, 0))
            ImageDraw.Draw(tmp).text((0, 0), emoji, font=self.emoji_font, embedded_color=True)
            bbox = tmp.getbbox()
            if not bbox:
                return
            cropped = tmp.crop(bbox)
            ratio = min(_FLAG_SIZE / cropped.width, _FLAG_SIZE / cropped.height)
            new_w = max(1, int(cropped.width * ratio))
            new_h = max(1, int(cropped.height * ratio))
            resized = cropped.resize((new_w, new_h), Resampling.LANCZOS)
            self.canvas.paste(
                resized.convert('RGB'),
                (cx - new_w // 2, cy - new_h // 2),
                resized.split()[3],
            )

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
    overlays: list[tuple[str | None, bytes | None]] | None = None,
    total_value: str | None = None,
) -> bytes:
    canvas = Image.new('RGB', (_CANVAS_W, _CANVAS_H), _CANVAS_BG)
    draw = ImageDraw.Draw(canvas)
    _draw_field(draw)
    _draw_formation_label(draw, formation.name)

    font = _load_font(_FONT_PATHS, _FONT_SIZE)
    emoji_font = _load_font_optional(_EMOJI_FONT_PATHS, _EMOJI_NATIVE_SIZE)
    renderer = _Renderer(canvas=canvas, draw=draw, font=font, emoji_font=emoji_font)
    for i, slot in enumerate(formation.slots):
        photo_bytes = photos[i] if i < len(photos) else None
        name = names[i] if i < len(names) else ''
        slot_overlays = overlays[i] if overlays and i < len(overlays) else None
        cx, cy = _field_xy(slot.x, slot.y)
        renderer.draw_player(photo_bytes, name, cx, cy, slot_overlays)

    if total_value:
        _draw_total_value(draw, total_value)

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
    ar = _CORNER_ARC_R
    k = _TOP_TAPER * _FW / _FH
    clip_bl = math.degrees(math.atan2(-1.0, k)) % 360
    clip_br = math.degrees(math.atan2(-1.0, -k)) % 360
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
    font = _load_font(_FONT_BOLD_PATHS, _FONT_LABEL_SIZE)
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


def _draw_total_value(draw: ImageDraw.ImageDraw, total_value: str) -> None:
    font = _load_font(_FONT_BOLD_PATHS, _FONT_LABEL_SIZE)
    field_bottom = _MY + _FH
    text_y = (field_bottom + _CANVAS_H - _FONT_LABEL_SIZE) // 2
    bbox = draw.textbbox((0, 0), total_value, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((_CANVAS_W - tw) // 2, text_y),
        total_value,
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
