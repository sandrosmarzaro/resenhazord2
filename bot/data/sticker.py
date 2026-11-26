STICKER_SIZE: tuple[int, int] = (512, 512)
MAX_ANIMATED_STICKER_BYTES = 500_000
MAX_STICKER_QUALITY = 95

# (fps, lowest quality) steps an animated sticker walks down until it fits the limit.
# People complain about choppy stickers more than blurry ones, so each step gives up a
# little quality before the next one drops frames, down to q10. libwebp encodes every
# frame whole, so 10 s of camera footage only fits at around 10-15 fps.
STICKER_FPS_LADDER: tuple[tuple[int, int], ...] = (
    (30, 50),
    (24, 35),
    (20, 25),
    (15, 10),
    (12, 10),
    (10, 10),
    (8, 10),
    (6, 10),
    (5, 10),
)

# Sticker types that fill the frame (cropping the overflow) instead of letterboxing.
COVER_STICKER_TYPES: frozenset[str] = frozenset({'crop', 'circle', 'rounded'})

# ffmpeg geq alpha expressions with the same shapes FrameShaper masks images with:
# a circle inscribed in the frame, and a rounded rectangle with a radius of 1/8.
VIDEO_ALPHA_MASKS: frozendict[str, str] = frozendict(
    {
        'circle': '255*lte(hypot(X+0.5-W/2,Y+0.5-H/2),W/2)',
        'rounded': (
            '255*lte(hypot(max(0,max(W/8-X-0.5,X+0.5-W+W/8)),max(0,max(H/8-Y-0.5,Y+0.5-H+H/8))),W/8)'
        ),
    }
)
