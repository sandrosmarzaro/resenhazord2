import io
from functools import partial
from typing import ClassVar

from PIL import Image

from bot.domain.services.sticker.animation import Animation
from bot.domain.services.sticker.frame_rate_ladder import EncodePlan, FrameRateLadder
from bot.domain.services.sticker.video_sticker_encoder import VideoStickerEncoder
from bot.infrastructure.work import Work


class AnimatedWebpEncoder:
    # libwebp's default effort, as ffmpeg and Pillow's still images use. Pillow saves
    # animations with method 0: ~40% bigger, and its size dips at some qualities (q89
    # halves the detail), which breaks the quality search.
    _METHOD: ClassVar[int] = 4

    # Pillow encoding is CPU-bound: off the event loop, the other in-flight commands
    # keep running.
    @classmethod
    async def encode(
        cls, buffer: bytes, sticker_type: str, max_quality: int, working_size: int
    ) -> bytes:
        animation = await Work.cpu(Animation.decode, buffer, sticker_type, working_size)
        ladder = FrameRateLadder(animation.clip(), partial(cls._frame_bytes, animation))
        return await ladder.fit(max_quality, partial(cls._encode, animation))

    @classmethod
    async def _frame_bytes(cls, animation: Animation, quality: int) -> int:
        sample = animation.sample(VideoStickerEncoder.SAMPLE_FRAMES)
        durations = animation.durations[: len(sample)]
        webp = await Work.cpu(cls._save, sample, durations, quality)
        return len(webp) // len(sample)

    @classmethod
    async def _encode(cls, animation: Animation, plan: EncodePlan) -> bytes:
        frames, durations = animation.at(plan.fps)
        return await Work.cpu(cls._save, frames, durations, plan.quality)

    @staticmethod
    def _save(frames: list[Image.Image], durations: list[int], quality: int) -> bytes:
        output = io.BytesIO()
        frames[0].save(
            output,
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            quality=quality,
            method=AnimatedWebpEncoder._METHOD,
        )
        return output.getvalue()
