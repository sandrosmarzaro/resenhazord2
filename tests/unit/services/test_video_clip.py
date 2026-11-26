import pytest

from bot.domain.services.sticker.video_clip import VideoClip

MAX_SECONDS = 10


def _probe(rate: str = '30/1', duration: str = '5.0') -> dict:
    return {'streams': [{'avg_frame_rate': rate}], 'format': {'duration': duration}}


class TestFromProbe:
    def test_reads_the_frame_rate_and_length(self) -> None:
        clip = VideoClip.from_probe(_probe('24000/1001', '8.008'), MAX_SECONDS)

        assert clip.fps == pytest.approx(23.976, abs=0.001)
        assert clip.seconds == pytest.approx(8.008)

    def test_caps_the_length(self) -> None:
        clip = VideoClip.from_probe(_probe(duration='15.0'), MAX_SECONDS)

        assert clip.seconds == MAX_SECONDS

    @pytest.mark.parametrize('rate', ['0/0', 'N/A', ''])
    def test_unknown_frame_rate_allows_the_highest_step(self, rate) -> None:
        clip = VideoClip.from_probe(_probe(rate=rate), MAX_SECONDS)

        assert clip.fps == VideoClip.UNKNOWN_FPS

    @pytest.mark.parametrize('duration', ['N/A', '0'])
    def test_unknown_length_counts_as_the_longest(self, duration) -> None:
        clip = VideoClip.from_probe(_probe(duration=duration), MAX_SECONDS)

        assert clip.seconds == MAX_SECONDS

    def test_a_file_without_video_still_gives_a_clip(self) -> None:
        clip = VideoClip.from_probe({}, MAX_SECONDS)

        assert clip == VideoClip(fps=VideoClip.UNKNOWN_FPS, seconds=MAX_SECONDS)


class TestFramesAt:
    def test_counts_every_started_frame(self) -> None:
        assert VideoClip(fps=24, seconds=8.008).frames_at(15) == 121
