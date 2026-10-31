"""Entry point for building the football field image."""

import io

from PIL import Image, ImageDraw

from bot.data.football_formations import Formation
from bot.domain.services.football_field.field_config import (
    DEFAULT_CONFIG,
    field_xy,
    load_font,
    load_font_optional,
)
from bot.domain.services.football_field.field_renderer import (
    draw_field,
    draw_formation_label,
    draw_total_value,
)
from bot.domain.services.football_field.player_renderer import PlayerRenderer


def build_football_field(
    photos: list[bytes | None],
    names: list[str],
    formation: Formation,
    overlays: list[tuple[str | None, bytes | None]] | None = None,
    total_value: str | None = None,
) -> bytes:
    renderer = _pitch(formation)
    for i, slot in enumerate(formation.slots):
        photo_bytes = photos[i] if i < len(photos) else None
        name = names[i] if i < len(names) else ''
        slot_overlays = overlays[i] if overlays and i < len(overlays) else None
        cx, cy = field_xy(slot.x, slot.y, renderer.cfg)
        renderer.draw_player(photo_bytes, name, cx, cy, slot_overlays)
    return _encode(renderer, total_value)


def build_card_field(cards: list[bytes | None], formation: Formation, label: str | None) -> bytes:
    renderer = _pitch(formation)
    for card, slot in zip(cards, formation.slots, strict=True):
        renderer.draw_card(card, *field_xy(slot.x, slot.y, renderer.cfg))
    return _encode(renderer, label)


def _pitch(formation: Formation) -> PlayerRenderer:
    cfg = DEFAULT_CONFIG
    canvas = Image.new('RGB', (cfg.canvas.width, cfg.canvas.height), cfg.canvas.background)
    draw = ImageDraw.Draw(canvas)
    draw_field(draw, cfg)
    draw_formation_label(draw, formation.name, cfg)
    font = load_font(cfg.fonts.paths, cfg.player.font_size)
    emoji_font = load_font_optional(cfg.fonts.emoji_paths, cfg.player.emoji_native_size)
    return PlayerRenderer(canvas=canvas, draw=draw, font=font, cfg=cfg, emoji_font=emoji_font)


def _encode(renderer: PlayerRenderer, label: str | None) -> bytes:
    if label:
        draw_total_value(renderer.draw, label, renderer.cfg)
    output = io.BytesIO()
    renderer.canvas.save(output, format='JPEG', quality=92)
    return output.getvalue()
