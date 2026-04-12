"""Player rendering and build_football_field entry point."""

import contextlib
import io
import unicodedata
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from bot.data.football_formations import Formation
from bot.domain.services.football_field.field_config import (
    DEFAULT_CONFIG,
    FieldConfig,
    PlayerDisplayConfig,
    field_xy,
    load_font,
    load_font_optional,
)
from bot.domain.services.football_field.field_renderer import (
    draw_field,
    draw_formation_label,
    draw_total_value,
)


class OverlayRenderer:
    def __init__(
        self,
        canvas: Image.Image,
        player_cfg: PlayerDisplayConfig,
        emoji_font: ImageFont.FreeTypeFont | None = None,
    ) -> None:
        self._canvas = canvas
        self._cfg = player_cfg
        self._emoji_font = emoji_font

    def render(
        self,
        overlays: tuple[str | None, bytes | None],
        cx: int,
        cy: int,
        r: int,
    ) -> None:
        ov_cy = cy + int(r * self._cfg.overlay_cy_ratio)
        ov_offset_x = int(r * self._cfg.overlay_offset_x_ratio)
        flag_emoji, badge_image = overlays
        if flag_emoji:
            self._draw_flag_emoji(flag_emoji, cx - ov_offset_x, ov_cy)
        if badge_image:
            self._draw_badge(badge_image, cx + ov_offset_x, ov_cy)

    def _draw_badge(self, img_bytes: bytes, cx: int, cy: int) -> None:
        with contextlib.suppress(Exception):
            img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
            size = self._cfg.badge_size
            ratio = min(size / img.width, size / img.height)
            new_w = max(1, int(img.width * ratio))
            new_h = max(1, int(img.height * ratio))
            img = img.resize((new_w, new_h), Resampling.LANCZOS)
            paste_x = cx - new_w // 2
            paste_y = cy - new_h // 2
            self._canvas.paste(img.convert('RGB'), (paste_x, paste_y), img.split()[3])

    def _draw_flag_emoji(self, emoji: str, cx: int, cy: int) -> None:
        if not self._emoji_font:
            return
        with contextlib.suppress(Exception):
            native = self._cfg.emoji_native_size
            tmp = Image.new('RGBA', (native * 2, native * 2), (0, 0, 0, 0))
            ImageDraw.Draw(tmp).text((0, 0), emoji, font=self._emoji_font, embedded_color=True)
            bbox = tmp.getbbox()
            if not bbox:
                return
            cropped = tmp.crop(bbox)
            size = self._cfg.flag_size
            ratio = min(size / cropped.width, size / cropped.height)
            new_w = max(1, int(cropped.width * ratio))
            new_h = max(1, int(cropped.height * ratio))
            resized = cropped.resize((new_w, new_h), Resampling.LANCZOS)
            self._canvas.paste(
                resized.convert('RGB'),
                (cx - new_w // 2, cy - new_h // 2),
                resized.split()[3],
            )


@dataclass
class PlayerRenderer:
    canvas: Image.Image
    draw: ImageDraw.ImageDraw
    font: ImageFont.FreeTypeFont
    cfg: FieldConfig = DEFAULT_CONFIG
    emoji_font: ImageFont.FreeTypeFont | None = None

    def __post_init__(self) -> None:
        self._overlay = OverlayRenderer(self.canvas, self.cfg.player, self.emoji_font)

    def draw_player(
        self,
        photo_bytes: bytes | None,
        name: str,
        cx: int,
        cy: int,
        overlays: tuple[str | None, bytes | None] | None = None,
    ) -> None:
        r = self.cfg.player.photo_diameter // 2
        if photo_bytes:
            self._paste_photo(photo_bytes, cx, cy, r)
        else:
            self._draw_placeholder(cx, cy, r)

        if overlays:
            self._overlay.render(overlays, cx, cy, r)

        self._draw_name_label(name, cx, cy, r)

    def _paste_photo(self, photo_bytes: bytes, cx: int, cy: int, r: int) -> None:
        d = self.cfg.player.photo_diameter
        with contextlib.suppress(OSError, ValueError):
            photo = Image.open(io.BytesIO(photo_bytes)).convert('RGBA')
            photo = photo.resize((d, d), Resampling.LANCZOS)
            bg = Image.new('RGBA', (d, d), (255, 255, 255, 255))
            bg.paste(photo, mask=photo.split()[3])
            mask = Image.new('L', (d, d), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, d, d], fill=255)
            self.canvas.paste(bg.convert('RGB'), (cx - r, cy - r), mask)

    def _draw_placeholder(self, cx: int, cy: int, r: int) -> None:
        self.draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill='#1b5e20',
            outline=self.cfg.field.line_color,
            width=4,
        )

    def _draw_name_label(self, name: str, cx: int, cy: int, r: int) -> None:
        short_name = shorten_name(name, self.cfg.player.name_max_len)
        bbox = self.draw.textbbox((0, 0), short_name, font=self.font)
        tw = bbox[2] - bbox[0]
        label_y = cy + r + 6
        self.draw.text(
            (cx - tw // 2, label_y),
            short_name,
            fill=self.cfg.field.line_color,
            font=self.font,
            stroke_width=self.cfg.player.stroke_width,
            stroke_fill='#000000',
        )


def shorten_name(name: str, max_len: int = 13) -> str:
    name = unicodedata.normalize('NFC', name)
    parts = name.split()
    if len(parts) <= 1:
        return name[:max_len]
    last = parts[-1]
    if len(last) > max_len:
        return last[:max_len]
    abbreviated = f'{parts[0][0]}. {last}'
    if len(abbreviated) <= max_len:
        return abbreviated
    return last


def build_football_field(
    photos: list[bytes | None],
    names: list[str],
    formation: Formation,
    overlays: list[tuple[str | None, bytes | None]] | None = None,
    total_value: str | None = None,
) -> bytes:
    cfg = DEFAULT_CONFIG
    canvas = Image.new('RGB', (cfg.canvas.width, cfg.canvas.height), cfg.canvas.background)
    draw = ImageDraw.Draw(canvas)
    draw_field(draw, cfg)
    draw_formation_label(draw, formation.name, cfg)

    font = load_font(cfg.fonts.paths, cfg.player.font_size)
    emoji_font = load_font_optional(cfg.fonts.emoji_paths, cfg.player.emoji_native_size)
    renderer = PlayerRenderer(canvas=canvas, draw=draw, font=font, cfg=cfg, emoji_font=emoji_font)
    for i, slot in enumerate(formation.slots):
        photo_bytes = photos[i] if i < len(photos) else None
        name = names[i] if i < len(names) else ''
        slot_overlays = overlays[i] if overlays and i < len(overlays) else None
        cx, cy = field_xy(slot.x, slot.y, cfg)
        renderer.draw_player(photo_bytes, name, cx, cy, slot_overlays)

    if total_value:
        draw_total_value(draw, total_value, cfg)

    output = io.BytesIO()
    canvas.save(output, format='JPEG', quality=92)
    return output.getvalue()
