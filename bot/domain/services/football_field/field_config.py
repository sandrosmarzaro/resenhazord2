"""Field geometry constants and coordinate mapping."""

import contextlib
from dataclasses import dataclass
from typing import cast

from PIL import ImageFont


@dataclass(frozen=True)
class FieldConfig:
    CANVAS_W: int = 2000
    CANVAS_H: int = 2750
    CANVAS_BG: str = '#000000'
    FIELD_COLOR: str = '#2e7d32'
    STRIPE_DARK: str = '#296e2c'
    STRIPE_LIGHT: str = '#327836'
    LINE_COLOR: str = '#ffffff'
    LINE_WIDTH: int = 12
    PHOTO_DIAMETER: int = 250
    FONT_SIZE: int = 40
    FONT_LABEL_SIZE: int = 69
    EMOJI_NATIVE_SIZE: int = 109
    NAME_MAX_LEN: int = 13
    STROKE_WIDTH: int = 5

    MX: int = 112
    MY: int = 175

    TOP_TAPER: float = 0.08
    N_LAWN_STRIPES: int = 14

    PENALTY_W_RATIO: float = 0.62
    PENALTY_H_RATIO: float = 0.18
    GOAL_W_RATIO: float = 0.32
    GOAL_H_RATIO: float = 0.08
    CIRCLE_R_RATIO: float = 0.10
    SPOT_R: int = 12
    PENALTY_SPOT_Y_RATIO: float = 0.12
    CORNER_ARC_R: int = 88
    PENALTY_ARC_R_RATIO: float = 0.12

    OVERLAY_CY_RATIO: float = 0.62
    OVERLAY_OFFSET_X_RATIO: float = 0.78

    FONT_PATHS: tuple[str, ...] = (
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    )
    FONT_BOLD_PATHS: tuple[str, ...] = (
        '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    )
    EMOJI_FONT_PATHS: tuple[str, ...] = (
        '/usr/share/fonts/noto/NotoColorEmoji.ttf',
        '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
    )

    @property
    def fw(self) -> int:
        return self.CANVAS_W - 2 * self.MX

    @property
    def fh(self) -> int:
        return self.CANVAS_H - 2 * self.MY

    @property
    def badge_size(self) -> int:
        return int(self.PHOTO_DIAMETER * 0.42)

    @property
    def flag_size(self) -> int:
        return int(self.PHOTO_DIAMETER * 0.36)


DEFAULT_CONFIG = FieldConfig()


def field_xy(x: float, y: float, cfg: FieldConfig = FieldConfig()) -> tuple[int, int]:
    taper = cfg.TOP_TAPER * (1.0 - y)
    left = cfg.MX + taper * cfg.fw
    width = cfg.fw * (1.0 - 2.0 * taper)
    return int(left + x * width), int(cfg.MY + y * cfg.fh)


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
