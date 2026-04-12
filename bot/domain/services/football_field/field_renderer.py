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
    font = load_font(cfg.fonts.bold_paths, cfg.player.font_label_size)
    name = unicodedata.normalize('NFKD', formation_name).encode('ascii', 'ignore').decode('ascii')
    bbox = draw.textbbox((0, 0), name, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((cfg.canvas.width - tw) // 2, cfg.canvas.margin_y // 3),
        name,
        fill=cfg.field.line_color,
        font=font,
        stroke_width=cfg.player.stroke_width,
        stroke_fill='#000000',
    )


def draw_total_value(
    draw: ImageDraw.ImageDraw, total_value: str, cfg: FieldConfig = DEFAULT_CONFIG
) -> None:
    font = load_font(cfg.fonts.bold_paths, cfg.player.font_label_size)
    field_bottom = cfg.canvas.margin_y + cfg.fh
    text_y = (field_bottom + cfg.canvas.height - cfg.player.font_label_size) // 2
    bbox = draw.textbbox((0, 0), total_value, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((cfg.canvas.width - tw) // 2, text_y),
        total_value,
        fill=cfg.field.line_color,
        font=font,
        stroke_width=cfg.player.stroke_width,
        stroke_fill='#000000',
    )


def _draw_lawn_stripes(draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
    for i in range(cfg.field.n_lawn_stripes):
        y0 = i / cfg.field.n_lawn_stripes
        y1 = (i + 1) / cfg.field.n_lawn_stripes
        color = cfg.field.stripe_dark if i % 2 == 0 else cfg.field.stripe_light
        corners = [
            field_xy(0, y0, cfg),
            field_xy(1, y0, cfg),
            field_xy(1, y1, cfg),
            field_xy(0, y1, cfg),
        ]
        draw.polygon(corners, fill=color)


def _draw_field_lines(draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
    lc = cfg.field.line_color
    lw = cfg.field.line_width

    draw.polygon(
        [field_xy(0, 0, cfg), field_xy(1, 0, cfg), field_xy(1, 1, cfg), field_xy(0, 1, cfg)],
        outline=lc,
        width=lw,
    )

    draw.line([field_xy(0, 0.5, cfg), field_xy(1, 0.5, cfg)], fill=lc, width=lw)

    ccx, ccy = field_xy(0.5, 0.5, cfg)
    circle_r = int(cfg.fh * cfg.field.circle_r_ratio)
    h_r = int(circle_r * (1.0 - cfg.field.top_taper))
    draw.ellipse([ccx - h_r, ccy - circle_r, ccx + h_r, ccy + circle_r], outline=lc, width=lw)
    spot_r = cfg.field.spot_r
    draw.ellipse([ccx - spot_r, ccy - spot_r, ccx + spot_r, ccy + spot_r], fill=lc)

    px0 = (1.0 - cfg.field.penalty_w_ratio) / 2.0
    px1 = 1.0 - px0
    ph = cfg.field.penalty_h_ratio
    gx0 = (1.0 - cfg.field.goal_w_ratio) / 2.0
    gx1 = 1.0 - gx0
    gh = cfg.field.goal_h_ratio

    for y0, y1 in ((0.0, ph), (1.0 - ph, 1.0)):
        draw.polygon(
            [
                field_xy(px0, y0, cfg),
                field_xy(px1, y0, cfg),
                field_xy(px1, y1, cfg),
                field_xy(px0, y1, cfg),
            ],
            outline=lc,
            width=lw,
        )

    for y0, y1 in ((0.0, gh), (1.0 - gh, 1.0)):
        draw.polygon(
            [
                field_xy(gx0, y0, cfg),
                field_xy(gx1, y0, cfg),
                field_xy(gx1, y1, cfg),
                field_xy(gx0, y1, cfg),
            ],
            outline=lc,
            width=lw,
        )

    spot_top = field_xy(0.5, cfg.field.penalty_spot_y_ratio, cfg)
    spot_bot = field_xy(0.5, 1.0 - cfg.field.penalty_spot_y_ratio, cfg)
    for sx, sy in (spot_top, spot_bot):
        draw.ellipse([sx - spot_r, sy - spot_r, sx + spot_r, sy + spot_r], fill=lc)

    _draw_corner_arcs(draw, cfg)
    _draw_penalty_arcs(draw, cfg, spot_top, spot_bot, ph)


def _draw_corner_arcs(draw: ImageDraw.ImageDraw, cfg: FieldConfig) -> None:
    ar = cfg.field.corner_arc_r
    lc = cfg.field.line_color
    lw = cfg.field.line_width
    k = cfg.field.top_taper * cfg.fw / cfg.fh
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
            fill=lc,
            width=lw,
        )


def _draw_penalty_arcs(
    draw: ImageDraw.ImageDraw,
    cfg: FieldConfig,
    spot_top: tuple[int, int],
    spot_bot: tuple[int, int],
    ph: float,
) -> None:
    pen_arc_r = int(cfg.fh * cfg.field.penalty_arc_r_ratio)
    lc = cfg.field.line_color
    lw = cfg.field.line_width

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
            fill=lc,
            width=lw,
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
            fill=lc,
            width=lw,
        )
