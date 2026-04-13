"""Field drawing — lawn stripes, labels, and total value."""

import unicodedata

from PIL import ImageDraw, ImageFont

from bot.domain.services.football_field.field_config import (
    DEFAULT_CONFIG,
    FieldConfig,
    field_xy,
    load_font,
)
from bot.domain.services.football_field.line_renderer import LineRenderer


def draw_field(draw: ImageDraw.ImageDraw, cfg: FieldConfig = DEFAULT_CONFIG) -> None:
    LawnRenderer(draw, cfg).render()
    LineRenderer(draw, cfg).render()


def draw_formation_label(
    draw: ImageDraw.ImageDraw, formation_name: str, cfg: FieldConfig = DEFAULT_CONFIG
) -> None:
    LabelRenderer(draw, cfg).render_formation(formation_name)


def draw_total_value(
    draw: ImageDraw.ImageDraw, total_value: str, cfg: FieldConfig = DEFAULT_CONFIG
) -> None:
    LabelRenderer(draw, cfg).render_total_value(total_value)


class LawnRenderer:
    def __init__(self, draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
        self._draw = draw
        self._cfg = cfg

    def render(self) -> None:
        fd = self._cfg.draw
        for i in range(fd.n_lawn_stripes):
            y0 = i / fd.n_lawn_stripes
            y1 = (i + 1) / fd.n_lawn_stripes
            color = fd.stripe_dark if i % 2 == 0 else fd.stripe_light
            corners = [
                field_xy(0, y0, self._cfg),
                field_xy(1, y0, self._cfg),
                field_xy(1, y1, self._cfg),
                field_xy(0, y1, self._cfg),
            ]
            self._draw.polygon(corners, fill=color)


class LabelRenderer:
    def __init__(self, draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
        self._draw = draw
        self._cfg = cfg

    def render_formation(self, formation_name: str) -> None:
        font = load_font(self._cfg.fonts.bold_paths, self._cfg.player.font_label_size)
        name = (
            unicodedata.normalize('NFKD', formation_name).encode('ascii', 'ignore').decode('ascii')
        )
        tw = self._text_width(name, font)
        self._draw.text(
            ((self._cfg.canvas.width - tw) // 2, self._cfg.canvas.margin_y // 3),
            name,
            fill=self._cfg.draw.line_color,
            font=font,
            stroke_width=self._cfg.player.stroke_width,
            stroke_fill='#000000',
        )

    def render_total_value(self, total_value: str) -> None:
        font = load_font(self._cfg.fonts.bold_paths, self._cfg.player.font_label_size)
        field_bottom = self._cfg.canvas.margin_y + self._cfg.fh
        text_y = (field_bottom + self._cfg.canvas.height - self._cfg.player.font_label_size) // 2
        tw = self._text_width(total_value, font)
        self._draw.text(
            ((self._cfg.canvas.width - tw) // 2, text_y),
            total_value,
            fill=self._cfg.draw.line_color,
            font=font,
            stroke_width=self._cfg.player.stroke_width,
            stroke_fill='#000000',
        )

    def _text_width(self, text: str, font: ImageFont.FreeTypeFont) -> int:
        bbox = self._draw.textbbox((0, 0), text, font=font)
        return int(bbox[2] - bbox[0])
