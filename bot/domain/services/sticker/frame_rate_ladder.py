from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import ClassVar

from bot.data.sticker import MAX_ANIMATED_STICKER_BYTES, STICKER_FPS_LADDER
from bot.domain.exceptions import StickerTooLargeError
from bot.domain.services.sticker.video_clip import VideoClip

type FrameBytes = Callable[[int], Awaitable[int]]


@dataclass(frozen=True)
class EncodePlan:
    fps: float
    quality: int


type Encode = Callable[[EncodePlan], Awaitable[bytes]]


class FrameRateLadder:
    # libwebp encodes every frame of an animation whole, so a sticker weighs its
    # frame count times the bytes one frame takes at that quality. frame_bytes measures
    # that on a sample of the clip, once per quality: each one costs an encode, so the
    # search stops this close to the best quality, a few percent of the size.
    QUALITY_TOLERANCE: ClassVar[int] = 4
    LOWEST_QUALITY: ClassVar[int] = min(floor for _, floor in STICKER_FPS_LADDER)
    # The sample misjudges a clip whose encoder reuses what didn't change between
    # frames: one more encode, aimed by how far the first one landed from the limit.
    MAX_ENCODES: ClassVar[int] = 2
    FULL_ENOUGH: ClassVar[float] = 0.9

    def __init__(self, clip: VideoClip, frame_bytes: FrameBytes) -> None:
        self._clip = clip
        self._frame_bytes = frame_bytes
        self._measured: dict[int, int] = {}

    async def fit(self, max_quality: int, encode: Encode) -> bytes:
        budget = MAX_ANIMATED_STICKER_BYTES
        fitting: bytes | None = None
        tried: EncodePlan | None = None
        for _ in range(self.MAX_ENCODES):
            plan = await self.plan(max_quality, budget)
            if plan == tried:
                break
            sticker = await encode(plan)
            tried = plan
            if len(sticker) <= MAX_ANIMATED_STICKER_BYTES:
                fitting = sticker
            if self._close_to_the_limit(sticker):
                break
            # Aim again by how far this plan's estimate missed its encode.
            budget = MAX_ANIMATED_STICKER_BYTES * self._estimate(plan) // len(sticker)
        if fitting is None:
            raise StickerTooLargeError
        return fitting

    async def plan(self, max_quality: int, budget: int) -> EncodePlan:
        lowest = min(self.LOWEST_QUALITY, max_quality)
        for fps, floor in self._steps(max_quality):
            # No quality fits a frame rate the lowest one misses.
            if not await self._fits(fps, lowest, budget):
                continue
            if await self._fits(fps, max_quality, budget):
                return EncodePlan(fps, max_quality)
            if await self._fits(fps, floor, budget):
                quality = await self._highest_quality(fps, floor, max_quality - 1, budget)
                return EncodePlan(fps, quality)
        raise StickerTooLargeError

    def _close_to_the_limit(self, sticker: bytes) -> bool:
        limit = MAX_ANIMATED_STICKER_BYTES
        return limit * self.FULL_ENOUGH <= len(sticker) <= limit

    def _steps(self, max_quality: int) -> Iterator[tuple[float, int]]:
        # Never above the source's frame rate: ffmpeg would only repeat frames.
        for fps, floor in STICKER_FPS_LADDER:
            yield min(fps, self._clip.fps), min(floor, max_quality)

    async def _highest_quality(self, fps: float, floor: int, ceiling: int, budget: int) -> int:
        while ceiling - floor > self.QUALITY_TOLERANCE:
            middle = (floor + ceiling + 1) // 2
            if await self._fits(fps, middle, budget):
                floor = middle
            else:
                ceiling = middle - 1
        return floor

    async def _fits(self, fps: float, quality: int, budget: int) -> bool:
        if quality not in self._measured:
            self._measured[quality] = await self._frame_bytes(quality)
        return self._estimate(EncodePlan(fps, quality)) <= budget

    def _estimate(self, plan: EncodePlan) -> int:
        return self._measured[plan.quality] * self._clip.frames_at(plan.fps)
