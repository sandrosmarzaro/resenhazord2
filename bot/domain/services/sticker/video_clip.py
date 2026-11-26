import math
from dataclasses import dataclass
from typing import Any, ClassVar

from bot.data.sticker import STICKER_FPS_LADDER


@dataclass(frozen=True)
class VideoClip:
    # ffprobe leaves out what it can't tell. Assuming the most keeps the ladder honest:
    # the fps filter only repeats frames, and a sticker is never longer than its cap.
    UNKNOWN_FPS: ClassVar[float] = STICKER_FPS_LADDER[0][0]

    fps: float
    seconds: float

    @classmethod
    def from_probe(cls, probe: dict[str, Any], max_seconds: float) -> VideoClip:
        streams: list[dict[str, str]] = probe.get('streams') or [{}]
        seconds = cls._number(probe.get('format', {}).get('duration', ''))
        return cls(
            fps=cls._number(streams[0].get('avg_frame_rate', '')) or cls.UNKNOWN_FPS,
            seconds=min(seconds, max_seconds) or max_seconds,
        )

    def frames_at(self, fps: float) -> int:
        return math.ceil(self.seconds * fps)

    @staticmethod
    def _number(value: str) -> float:
        numerator, _, denominator = value.partition('/')
        try:
            return float(numerator) / float(denominator or 1)
        except ValueError, ZeroDivisionError:
            return 0
