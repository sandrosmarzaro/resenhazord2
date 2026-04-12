"""Field drawing — lawn stripes, lines, labels, and total value."""

import math
import unicodedata

from PIL import ImageDraw

from bot.domain.services.football_field.field_config import (
    DEFAULT_CONFIG,
    FieldConfig,
    field_xy,
    load_font,
)


def draw_field(draw: ImageDraw.ImageDraw, cfg: FieldConfig = DEFAULT_CONFIG) -> None:
    _draw_lawn_stripes(draw, cfg)
    _draw_field_lines(draw, cfg)


def draw_formation_label(
    draw: ImageDraw.ImageDraw, formation_name: str, cfg: FieldConfig = DEFAULT_CONFIG
) -> None:
    font = load_font(cfg.FONT_BOLD_PATHS, cfg.FONT_LABEL_SIZE)
    name = unicodedata.normalize('NFKD', formation_name).encode('ascii', 'ignore').decode('ascii')
    bbox = draw.textbbox((0, 0), name, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((cfg.CANVAS_W - tw) // 2, cfg.MY // 3),
        name,
        fill=cfg.LINE_COLOR,
        font=font,
        stroke_width=cfg.STROKE_WIDTH,
        stroke_fill='#000000',
    )


def draw_total_value(
    draw: ImageDraw.ImageDraw, total_value: str, cfg: FieldConfig = DEFAULT_CONFIG
) -> None:
    font = load_font(cfg.FONT_BOLD_PATHS, cfg.FONT_LABEL_SIZE)
    field_bottom = cfg.MY + cfg.fh
    text_y = (field_bottom + cfg.CANVAS_H - cfg.FONT_LABEL_SIZE) // 2
    bbox = draw.textbbox((0, 0), total_value, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((cfg.CANVAS_W - tw) // 2, text_y),
        total_value,
        fill=cfg.LINE_COLOR,
        font=font,
        stroke_width=cfg.STROKE_WIDTH,
        stroke_fill='#000000',
    )


def _draw_lawn_stripes(draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
    for i in range(cfg.N_LAWN_STRIPES):
        y0 = i / cfg.N_LAWN_STRIPES
        y1 = (i + 1) / cfg.N_LAWN_STRIPES
        color = cfg.STRIPE_DARK if i % 2 == 0 else cfg.STRIPE_LIGHT
        corners = [
            field_xy(0, y0, cfg),
            field_xy(1, y0, cfg),
            field_xy(1, y1, cfg),
            field_xy(0, y1, cfg),
        ]
        draw.polygon(corners, fill=color)


def _draw_field_lines(draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
    draw.polygon(
        [field_xy(0, 0, cfg), field_xy(1, 0, cfg), field_xy(1, 1, cfg), field_xy(0, 1, cfg)],
        outline=cfg.LINE_COLOR,
        width=cfg.LINE_WIDTH,
    )

    draw.line(
        [field_xy(0, 0.5, cfg), field_xy(1, 0.5, cfg)], fill=cfg.LINE_COLOR, width=cfg.LINE_WIDTH
    )

    ccx, ccy = field_xy(0.5, 0.5, cfg)
    circle_r = int(cfg.fh * cfg.CIRCLE_R_RATIO)
    h_r = int(circle_r * (1.0 - cfg.TOP_TAPER))
    draw.ellipse(
        [ccx - h_r, ccy - circle_r, ccx + h_r, ccy + circle_r],
        outline=cfg.LINE_COLOR,
        width=cfg.LINE_WIDTH,
    )
    draw.ellipse(
        [ccx - cfg.SPOT_R, ccy - cfg.SPOT_R, ccx + cfg.SPOT_R, ccy + cfg.SPOT_R],
        fill=cfg.LINE_COLOR,
    )

    px0 = (1.0 - cfg.PENALTY_W_RATIO) / 2.0
    px1 = 1.0 - px0
    ph = cfg.PENALTY_H_RATIO
    gx0 = (1.0 - cfg.GOAL_W_RATIO) / 2.0
    gx1 = 1.0 - gx0
    gh = cfg.GOAL_H_RATIO

    for y0, y1 in ((0.0, ph), (1.0 - ph, 1.0)):
        draw.polygon(
            [
                field_xy(px0, y0, cfg),
                field_xy(px1, y0, cfg),
                field_xy(px1, y1, cfg),
                field_xy(px0, y1, cfg),
            ],
            outline=cfg.LINE_COLOR,
            width=cfg.LINE_WIDTH,
        )

    for y0, y1 in ((0.0, gh), (1.0 - gh, 1.0)):
        draw.polygon(
            [
                field_xy(gx0, y0, cfg),
                field_xy(gx1, y0, cfg),
                field_xy(gx1, y1, cfg),
                field_xy(gx0, y1, cfg),
            ],
            outline=cfg.LINE_COLOR,
            width=cfg.LINE_WIDTH,
        )

    spot_top = field_xy(0.5, cfg.PENALTY_SPOT_Y_RATIO, cfg)
    spot_bot = field_xy(0.5, 1.0 - cfg.PENALTY_SPOT_Y_RATIO, cfg)
    for sx, sy in (spot_top, spot_bot):
        draw.ellipse(
            [sx - cfg.SPOT_R, sy - cfg.SPOT_R, sx + cfg.SPOT_R, sy + cfg.SPOT_R],
            fill=cfg.LINE_COLOR,
        )

    _draw_corner_arcs(draw, cfg)
    _draw_penalty_arcs(draw, cfg, spot_top, spot_bot, ph)


def _draw_corner_arcs(draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
    ar = cfg.CORNER_ARC_R
    k = cfg.TOP_TAPER * cfg.fw / cfg.fh
    clip_bl = math.degrees(math.atan2(-1.0, k)) % 360
    clip_br = math.degrees(math.atan2(-1.0, -k)) % 360
    for (cx_c, cy_c), start, end in [
        (field_xy(0, 0, cfg), 0, 90),
        (field_xy(1, 0, cfg), 90, 180),
        (field_xy(0, 1, cfg), clip_bl, 360),
        (field_xy(1, 1, cfg), 180, clip_br),
    ]:
        draw.arc(
            [cx_c - ar, cy_c - ar, cx_c + ar, cy_c + ar],
            start=start,
            end=end,
            fill=cfg.LINE_COLOR,
            width=cfg.LINE_WIDTH,
        )


def _draw_penalty_arcs(
    draw: ImageDraw.ImageDraw,
    cfg: FieldConfig,
    spot_top: tuple[int, int],
    spot_bot: tuple[int, int],
    ph: float,
) -> None:
    pen_arc_r = int(cfg.fh * cfg.PENALTY_ARC_R_RATIO)

    spot_bx, spot_by = spot_bot
    box_top_y = field_xy(0.5, 1.0 - ph, cfg)[1]
    d_bot = spot_by - box_top_y
    if pen_arc_r > d_bot > 0:
        h_bot = math.sqrt(pen_arc_r**2 - d_bot**2)
        a1 = math.degrees(math.atan2(-d_bot, -h_bot)) % 360
        a2 = math.degrees(math.atan2(-d_bot, h_bot)) % 360
        draw.arc(
            [spot_bx - pen_arc_r, spot_by - pen_arc_r, spot_bx + pen_arc_r, spot_by + pen_arc_r],
            start=a1,
            end=a2,
            fill=cfg.LINE_COLOR,
            width=cfg.LINE_WIDTH,
        )

    spot_tx, spot_ty = spot_top
    box_bot_y = field_xy(0.5, ph, cfg)[1]
    d_top = box_bot_y - spot_ty
    if pen_arc_r > d_top > 0:
        h_top = math.sqrt(pen_arc_r**2 - d_top**2)
        a1_top = math.degrees(math.atan2(d_top, h_top)) % 360
        a2_top = math.degrees(math.atan2(d_top, -h_top)) % 360
        draw.arc(
            [spot_tx - pen_arc_r, spot_ty - pen_arc_r, spot_tx + pen_arc_r, spot_ty + pen_arc_r],
            start=a1_top,
            end=a2_top,
            fill=cfg.LINE_COLOR,
            width=cfg.LINE_WIDTH,
        )
