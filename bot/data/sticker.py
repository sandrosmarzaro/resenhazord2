STICKER_SIZE: tuple[int, int] = (512, 512)
MAX_FRAME_STRIDE = 4
MAX_ANIMATED_STICKER_BYTES = 500_000

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
