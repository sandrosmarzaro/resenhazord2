from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass

from bot.data.sticker import STICKER_FPS_LADDER
from bot.domain.exceptions import StickerTooLargeError
from bot.domain.services.sticker.video_clip import VideoClip

type FrameBytes = Callable[[int], Awaitable[int]]


@dataclass(frozen=True)
class EncodePlan:
    fps: float
    quality: int


class FrameRateLadder:
    # libwebp encodes every frame of an animation whole, so a sticker weighs its
    # frame count times the bytes one frame takes at that quality. frame_bytes measures
    # that on a sample of the clip, once per quality.
    def __init__(self, clip: VideoClip, frame_bytes: FrameBytes) -> None:
        self._clip = clip
        self._frame_bytes = frame_bytes
        self._measured: dict[int, int] = {}

    async def plan(self, max_quality: int, budget: int) -> EncodePlan:
        for fps, floor in self._steps(max_quality):
            if await self._fits(fps, floor, budget):
                return EncodePlan(fps, await self._highest_quality(fps, floor, max_quality, budget))
        raise StickerTooLargeError

    def _steps(self, max_quality: int) -> Iterator[tuple[float, int]]:
        # Never above the source's frame rate: ffmpeg would only repeat frames.
        for fps, floor in STICKER_FPS_LADDER:
            yield min(fps, self._clip.fps), min(floor, max_quality)

    async def _highest_quality(self, fps: float, floor: int, ceiling: int, budget: int) -> int:
        while floor < ceiling:
            middle = (floor + ceiling + 1) // 2
            if await self._fits(fps, middle, budget):
                floor = middle
            else:
                ceiling = middle - 1
        return floor

    async def _fits(self, fps: float, quality: int, budget: int) -> bool:
        if quality not in self._measured:
            self._measured[quality] = await self._frame_bytes(quality)
        return self._measured[quality] * self._clip.frames_at(fps) <= budget
