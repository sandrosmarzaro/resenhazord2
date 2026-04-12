"""Field line drawing — boundary, midline, circles, penalty/goal areas, arcs."""

import math

from PIL import ImageDraw

from bot.domain.services.football_field.field_config import FieldConfig, field_xy


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
        self._draw_box_pair(self._cfg.draw.penalty_w_ratio, self._cfg.draw.penalty_h_ratio)

    def _draw_goal_areas(self) -> None:
        self._draw_box_pair(self._cfg.draw.goal_w_ratio, self._cfg.draw.goal_h_ratio)

    def _draw_box_pair(self, w_ratio: float, h_ratio: float) -> None:
        cfg = self._cfg
        x0 = (1.0 - w_ratio) / 2.0
        x1 = 1.0 - x0
        for y0, y1 in ((0.0, h_ratio), (1.0 - h_ratio, 1.0)):
            self._draw.polygon(
                [
                    field_xy(x0, y0, cfg),
                    field_xy(x1, y0, cfg),
                    field_xy(x1, y1, cfg),
                    field_xy(x0, y1, cfg),
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
        pen_arc_r = int(cfg.fh * cfg.draw.penalty_arc_r_ratio)
        ph = cfg.draw.penalty_h_ratio
        self._draw_single_penalty_arc(spot_bot, field_xy(0.5, 1.0 - ph, cfg)[1], pen_arc_r, -1)
        self._draw_single_penalty_arc(spot_top, field_xy(0.5, ph, cfg)[1], pen_arc_r, 1)

    def _draw_single_penalty_arc(
        self, spot: tuple[int, int], box_edge_y: int, arc_r: int, sign: int
    ) -> None:
        sx, sy = spot
        d = sign * (box_edge_y - sy)
        if not (arc_r > d > 0):
            return
        h = math.sqrt(arc_r**2 - d**2)
        a1 = math.degrees(math.atan2(sign * d, -sign * h)) % 360
        a2 = math.degrees(math.atan2(sign * d, sign * h)) % 360
        self._draw.arc(
            [sx - arc_r, sy - arc_r, sx + arc_r, sy + arc_r],
            start=a1,
            end=a2,
            fill=self._lc,
            width=self._lw,
        )

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
