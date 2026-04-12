"""Field drawing — lawn stripes, lines, labels, and total value."""

import math
import unicodedata

from PIL import ImageDraw, ImageFont

from bot.domain.services.football_field.field_config import (
    DEFAULT_CONFIG,
    FieldConfig,
    field_xy,
    load_font,
)


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


class LineRenderer:
    def __init__(self, draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
        self._draw = draw
        self._cfg = cfg
        self._lc = cfg.draw.line_color
        self._lw = cfg.draw.line_width

    def render(self) -> None:
        self._draw_boundary()
        self._draw_midline()
        self._draw_center_circle()
        self._draw_penalty_areas()
        self._draw_goal_areas()
        self._draw_penalty_spots()
        self._draw_corner_arcs()

    def _draw_boundary(self) -> None:
        cfg = self._cfg
        self._draw.polygon(
            [
                field_xy(0, 0, cfg),
                field_xy(1, 0, cfg),
                field_xy(1, 1, cfg),
                field_xy(0, 1, cfg),
            ],
            outline=self._lc,
            width=self._lw,
        )

    def _draw_midline(self) -> None:
        cfg = self._cfg
        self._draw.line(
            [field_xy(0, 0.5, cfg), field_xy(1, 0.5, cfg)], fill=self._lc, width=self._lw
        )

    def _draw_center_circle(self) -> None:
        cfg = self._cfg
        ccx, ccy = field_xy(0.5, 0.5, cfg)
        circle_r = int(cfg.fh * cfg.draw.circle_r_ratio)
        h_r = int(circle_r * (1.0 - cfg.draw.top_taper))
        self._draw.ellipse(
            [ccx - h_r, ccy - circle_r, ccx + h_r, ccy + circle_r],
            outline=self._lc,
            width=self._lw,
        )
        spot_r = cfg.draw.spot_r
        self._draw.ellipse([ccx - spot_r, ccy - spot_r, ccx + spot_r, ccy + spot_r], fill=self._lc)

    def _draw_penalty_areas(self) -> None:
        cfg = self._cfg
        px0 = (1.0 - cfg.draw.penalty_w_ratio) / 2.0
        px1 = 1.0 - px0
        ph = cfg.draw.penalty_h_ratio
        for y0, y1 in ((0.0, ph), (1.0 - ph, 1.0)):
            self._draw.polygon(
                [
                    field_xy(px0, y0, cfg),
                    field_xy(px1, y0, cfg),
                    field_xy(px1, y1, cfg),
                    field_xy(px0, y1, cfg),
                ],
                outline=self._lc,
                width=self._lw,
            )

    def _draw_goal_areas(self) -> None:
        cfg = self._cfg
        gx0 = (1.0 - cfg.draw.goal_w_ratio) / 2.0
        gx1 = 1.0 - gx0
        gh = cfg.draw.goal_h_ratio
        for y0, y1 in ((0.0, gh), (1.0 - gh, 1.0)):
            self._draw.polygon(
                [
                    field_xy(gx0, y0, cfg),
                    field_xy(gx1, y0, cfg),
                    field_xy(gx1, y1, cfg),
                    field_xy(gx0, y1, cfg),
                ],
                outline=self._lc,
                width=self._lw,
            )

    def _draw_penalty_spots(self) -> None:
        cfg = self._cfg
        spot_r = cfg.draw.spot_r
        spot_top = field_xy(0.5, cfg.draw.penalty_spot_y_ratio, cfg)
        spot_bot = field_xy(0.5, 1.0 - cfg.draw.penalty_spot_y_ratio, cfg)
        for sx, sy in (spot_top, spot_bot):
            self._draw.ellipse([sx - spot_r, sy - spot_r, sx + spot_r, sy + spot_r], fill=self._lc)
        self._draw_penalty_arcs(spot_top, spot_bot, cfg.draw.penalty_h_ratio)

    def _draw_corner_arcs(self) -> None:
        cfg = self._cfg
        ar = cfg.draw.corner_arc_r
        k = cfg.draw.top_taper * cfg.fw / cfg.fh
        clip_bl = math.degrees(math.atan2(-1.0, k)) % 360
        clip_br = math.degrees(math.atan2(-1.0, -k)) % 360
        for (cx_c, cy_c), start, end in [
            (field_xy(0, 0, cfg), 0, 90),
            (field_xy(1, 0, cfg), 90, 180),
            (field_xy(0, 1, cfg), clip_bl, 360),
            (field_xy(1, 1, cfg), 180, clip_br),
        ]:
            self._draw.arc(
                [cx_c - ar, cy_c - ar, cx_c + ar, cy_c + ar],
                start=start,
                end=end,
                fill=self._lc,
                width=self._lw,
            )

    def _draw_penalty_arcs(
        self,
        spot_top: tuple[int, int],
        spot_bot: tuple[int, int],
        ph: float,
    ) -> None:
        cfg = self._cfg
        pen_arc_r = int(cfg.fh * cfg.draw.penalty_arc_r_ratio)

        spot_bx, spot_by = spot_bot
        box_top_y = field_xy(0.5, 1.0 - ph, cfg)[1]
        d_bot = spot_by - box_top_y
        if pen_arc_r > d_bot > 0:
            h_bot = math.sqrt(pen_arc_r**2 - d_bot**2)
            a1 = math.degrees(math.atan2(-d_bot, -h_bot)) % 360
            a2 = math.degrees(math.atan2(-d_bot, h_bot)) % 360
            self._draw.arc(
                [
                    spot_bx - pen_arc_r,
                    spot_by - pen_arc_r,
                    spot_bx + pen_arc_r,
                    spot_by + pen_arc_r,
                ],
                start=a1,
                end=a2,
                fill=self._lc,
                width=self._lw,
            )

        spot_tx, spot_ty = spot_top
        box_bot_y = field_xy(0.5, ph, cfg)[1]
        d_top = box_bot_y - spot_ty
        if pen_arc_r > d_top > 0:
            h_top = math.sqrt(pen_arc_r**2 - d_top**2)
            a1_top = math.degrees(math.atan2(d_top, h_top)) % 360
            a2_top = math.degrees(math.atan2(d_top, -h_top)) % 360
            self._draw.arc(
                [
                    spot_tx - pen_arc_r,
                    spot_ty - pen_arc_r,
                    spot_tx + pen_arc_r,
                    spot_ty + pen_arc_r,
                ],
                start=a1_top,
                end=a2_top,
                fill=self._lc,
                width=self._lw,
            )
