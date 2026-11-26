import io

import pytest
from PIL import Image

from bot.data.sticker import STICKER_SIZE
from bot.domain.services.sticker.animation import Animation
from bot.domain.services.sticker.video_clip import VideoClip


def _animation(durations: list[int]) -> Animation:
    frames = [Image.new('RGBA', STICKER_SIZE, (i, 0, 0, 255)) for i in range(len(durations))]
    return Animation(frames=frames, durations=durations)


def _reds(frames: list[Image.Image]) -> list[int]:
    return [frame.tobytes()[0] for frame in frames]


class TestDecode:
    def test_shapes_every_frame_and_reads_its_duration(self) -> None:
        source = [Image.new('RGBA', (100, 80), color) for color in ('red', 'blue')]
        buffer = io.BytesIO()
        source[0].save(
            buffer, format='WEBP', save_all=True, append_images=source[1:], duration=[40, 60]
        )

        animation = Animation.decode(buffer.getvalue(), 'full', STICKER_SIZE[0])

        assert [frame.size for frame in animation.frames] == [STICKER_SIZE, STICKER_SIZE]
        assert animation.durations == [40, 60]


class TestClip:
    def test_spans_the_whole_animation(self) -> None:
        clip = _animation([50] * 20).clip()

        assert clip == VideoClip(fps=20, seconds=1)


class TestAt:
    def test_keeps_every_frame_at_the_source_frame_rate(self) -> None:
        frames, durations = _animation([50] * 4).at(20)

        assert (_reds(frames), durations) == ([0, 1, 2, 3], [50] * 4)

    def test_keeps_every_frame_of_rounded_durations_at_their_own_frame_rate(self) -> None:
        # 24 fps in whole milliseconds.
        animation = _animation([42, 41, 42] * 4)

        frames, _ = animation.at(animation.clip().fps)

        assert len(frames) == len(animation.frames)

    def test_drops_frames_and_keeps_the_timing(self) -> None:
        frames, durations = _animation([50] * 6).at(10)

        assert (_reds(frames), durations) == ([0, 2, 4], [100] * 3)

    def test_keeps_the_frames_after_a_long_one(self) -> None:
        frames, durations = _animation([2_000, 100, 100]).at(10)

        assert (_reds(frames), durations) == ([0, 1, 2], [2_000, 100, 100])


class TestSample:
    def test_spreads_over_the_animation(self) -> None:
        sample = _animation([50] * 40).sample(4)

        assert _reds(sample) == [0, 10, 20, 30]

    @pytest.mark.parametrize('count', [4, 20])
    def test_takes_every_frame_of_a_short_animation(self, count) -> None:
        sample = _animation([50] * 3).sample(count)

        assert _reds(sample) == [0, 1, 2]
