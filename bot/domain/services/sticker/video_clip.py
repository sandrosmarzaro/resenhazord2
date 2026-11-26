import math
from dataclasses import dataclass


@dataclass(frozen=True)
class VideoClip:
    fps: float
    seconds: float

    def frames_at(self, fps: float) -> int:
        return math.ceil(self.seconds * fps)
