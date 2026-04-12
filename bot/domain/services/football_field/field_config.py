"""Field geometry constants and coordinate mapping."""

import contextlib
from dataclasses import dataclass
from typing import cast

from PIL import ImageFont


@dataclass(frozen=True)
class CanvasConfig:
    width: int = 2000
    height: int = 2750
    background: str = '#000000'
    margin_x: int = 112
    margin_y: int = 175


@dataclass(frozen=True)
class FieldDrawConfig:
    color: str = '#2e7d32'
    stripe_dark: str = '#296e2c'
    stripe_light: str = '#327836'
    line_color: str = '#ffffff'
    line_width: int = 12
    top_taper: float = 0.08
    n_lawn_stripes: int = 14
    penalty_w_ratio: float = 0.62
    penalty_h_ratio: float = 0.18
    goal_w_ratio: float = 0.32
    goal_h_ratio: float = 0.08
    circle_r_ratio: float = 0.10
    spot_r: int = 12
    penalty_spot_y_ratio: float = 0.12
    corner_arc_r: int = 88
    penalty_arc_r_ratio: float = 0.12


@dataclass(frozen=True)
class PlayerDisplayConfig:
    photo_diameter: int = 250
    font_size: int = 40
    font_label_size: int = 69
    emoji_native_size: int = 109
    name_max_len: int = 13
    stroke_width: int = 5
    overlay_cy_ratio: float = 0.62
    overlay_offset_x_ratio: float = 0.78

    @property
    def badge_size(self) -> int:
        return int(self.photo_diameter * 0.42)

    @property
    def flag_size(self) -> int:
        return int(self.photo_diameter * 0.36)


@dataclass(frozen=True)
class FontConfig:
    paths: tuple[str, ...] = (
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    )
    bold_paths: tuple[str, ...] = (
        '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    )
    emoji_paths: tuple[str, ...] = (
        '/usr/share/fonts/noto/NotoColorEmoji.ttf',
        '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
    )


@dataclass(frozen=True)
class FieldConfig:
    canvas: CanvasConfig = CanvasConfig()
    field: FieldDrawConfig = FieldDrawConfig()
    player: PlayerDisplayConfig = PlayerDisplayConfig()
    fonts: FontConfig = FontConfig()

    @property
    def fw(self) -> int:
        return self.canvas.width - 2 * self.canvas.margin_x

    @property
    def fh(self) -> int:
        return self.canvas.height - 2 * self.canvas.margin_y


DEFAULT_CONFIG = FieldConfig()


def field_xy(x: float, y: float, cfg: FieldConfig = DEFAULT_CONFIG) -> tuple[int, int]:
    taper = cfg.field.top_taper * (1.0 - y)
    left = cfg.canvas.margin_x + taper * cfg.fw
    width = cfg.fw * (1.0 - 2.0 * taper)
    return int(left + x * width), int(cfg.canvas.margin_y + y * cfg.fh)


def load_font(paths: tuple[str, ...] | list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in paths:
        with contextlib.suppress(OSError):
            return ImageFont.truetype(path, size)
    return cast('ImageFont.FreeTypeFont', ImageFont.load_default(size=size))


def load_font_optional(
    paths: tuple[str, ...] | list[str], size: int
) -> ImageFont.FreeTypeFont | None:
    for path in paths:
        with contextlib.suppress(OSError):
            return ImageFont.truetype(path, size)
    return None
