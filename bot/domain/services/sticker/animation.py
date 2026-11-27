import io
from dataclasses import dataclass

from PIL import Image

from bot.domain.services.sticker.frame_shaper import FrameShaper
from bot.domain.services.sticker.media_format import MediaFormat
from bot.domain.services.sticker.video_clip import VideoClip

type Frames = tuple[list[Image.Image], list[int]]


@dataclass(frozen=True)
class Animation:
    frames: list[Image.Image]
    durations: list[int]

    @classmethod
    def decode(cls, buffer: bytes, sticker_type: str, working_size: int) -> Animation:
        source = Image.open(io.BytesIO(buffer))
        count = getattr(source, 'n_frames', 1)
        frames = []
        for i in range(count):
            source.seek(i)
            frames.append(FrameShaper.shape(source.convert('RGBA'), sticker_type, working_size))
        return cls(frames, MediaFormat.frame_durations(buffer, count))

    def clip(self) -> VideoClip:
        seconds = sum(self.durations) / 1000
        return VideoClip(fps=len(self.frames) / seconds, seconds=seconds)

    # The first frame centred in each 1/fps slot stands for it, holding until the next
    # one: a frame held longer than a slot keeps its whole time. Centres, not starts:
    # durations rounded to whole milliseconds would put starts on the slot edges.
    def at(self, fps: float) -> Frames:
        frames: list[Image.Image] = []
        durations: list[int] = []
        last_slot = -1
        elapsed = 0
        for frame, duration in zip(self.frames, self.durations, strict=True):
            slot = (2 * elapsed + duration) * fps // 2000
            if slot > last_slot:
                frames.append(frame)
                durations.append(duration)
                last_slot = slot
            else:
                durations[-1] += duration
            elapsed += duration
        return frames, durations

    def sample(self, count: int) -> list[Image.Image]:
        total = len(self.frames)
        taken = min(count, total)
        return [self.frames[i * total // taken] for i in range(taken)]
