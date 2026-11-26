import pytest

from bot.domain.exceptions import StickerTooLargeError
from bot.domain.services.sticker.frame_rate_ladder import EncodePlan, FrameRateLadder
from bot.domain.services.sticker.video_clip import VideoClip

BUDGET = 500_000
BYTES_PER_QUALITY_POINT = 100


class FrameSizes:
    def __init__(
        self, bytes_per_quality_point: int = BYTES_PER_QUALITY_POINT, base: int = 0
    ) -> None:
        self.bytes_per_quality_point = bytes_per_quality_point
        self.base = base
        self.measured: list[int] = []

    async def __call__(self, quality: int) -> int:
        self.measured.append(quality)
        return self.base + quality * self.bytes_per_quality_point


def _assert_close_below(quality: int, best: int) -> None:
    assert best - FrameRateLadder.QUALITY_TOLERANCE <= quality <= best


def _ladder(fps: float, seconds: float, frame_sizes: FrameSizes | None = None) -> FrameRateLadder:
    return FrameRateLadder(VideoClip(fps=fps, seconds=seconds), frame_sizes or FrameSizes())


class TestFullFrameRate:
    @pytest.mark.anyio
    async def test_short_clip_keeps_30_fps_at_the_highest_quality(self) -> None:
        plan = await _ladder(fps=30, seconds=1).plan(max_quality=95, budget=BUDGET)

        assert plan == EncodePlan(fps=30, quality=95)

    @pytest.mark.anyio
    async def test_picks_the_highest_quality_that_fits(self) -> None:
        # 60 frames x q x 100 bytes fits 500 kB up to q83.
        plan = await _ladder(fps=30, seconds=2).plan(max_quality=95, budget=BUDGET)

        assert plan.fps == 30
        _assert_close_below(plan.quality, best=83)

    @pytest.mark.anyio
    async def test_never_goes_above_the_source_frame_rate(self) -> None:
        plan = await _ladder(fps=12, seconds=1).plan(max_quality=95, budget=BUDGET)

        assert plan == EncodePlan(fps=12, quality=95)


class TestTradingFramesForQuality:
    @pytest.mark.anyio
    async def test_drops_frames_once_quality_reaches_the_floor_of_the_step(self) -> None:
        # 30 fps fits only at q16 and 24 fps at q20, under their q50 and q35 floors.
        plan = await _ladder(fps=30, seconds=10).plan(max_quality=95, budget=BUDGET)

        assert plan == EncodePlan(fps=20, quality=25)

    @pytest.mark.anyio
    async def test_slow_source_reaches_the_lower_floor_at_its_own_frame_rate(self) -> None:
        # 120 frames fit up to q41: under the q50 floor of the first step, but the
        # next, lower floors accept it.
        plan = await _ladder(fps=12, seconds=10).plan(max_quality=95, budget=BUDGET)

        assert plan.fps == 12
        _assert_close_below(plan.quality, best=41)

    @pytest.mark.anyio
    async def test_refuses_a_clip_that_fits_no_step(self) -> None:
        ladder = _ladder(fps=30, seconds=10, frame_sizes=FrameSizes(BUDGET))

        with pytest.raises(StickerTooLargeError):
            await ladder.plan(max_quality=95, budget=BUDGET)


class TestUserQualityReduction:
    @pytest.mark.anyio
    async def test_caps_the_quality(self) -> None:
        plan = await _ladder(fps=30, seconds=1).plan(max_quality=40, budget=BUDGET)

        assert plan == EncodePlan(fps=30, quality=40)

    @pytest.mark.anyio
    async def test_keeps_the_frame_rate_when_the_cap_is_under_the_floor(self) -> None:
        plan = await _ladder(fps=30, seconds=10).plan(max_quality=10, budget=BUDGET)

        assert plan == EncodePlan(fps=30, quality=10)


class TestMeasurements:
    @pytest.mark.anyio
    async def test_a_clip_that_fits_at_the_highest_quality_takes_two_measurements(self) -> None:
        frame_sizes = FrameSizes()

        await _ladder(fps=30, seconds=1, frame_sizes=frame_sizes).plan(
            max_quality=95, budget=BUDGET
        )

        assert frame_sizes.measured == [10, 95]

    @pytest.mark.anyio
    async def test_skips_the_floor_of_a_frame_rate_the_lowest_quality_misses(self) -> None:
        # Every frame weighs 2 kB: 300 of them miss the budget, 240 fit.
        frame_sizes = FrameSizes(bytes_per_quality_point=0, base=2_000)

        plan = await _ladder(fps=30, seconds=10, frame_sizes=frame_sizes).plan(
            max_quality=95, budget=BUDGET
        )

        assert plan == EncodePlan(fps=24, quality=95)
        assert frame_sizes.measured == [10, 95]

    @pytest.mark.anyio
    async def test_measures_each_quality_once_across_plans(self) -> None:
        frame_sizes = FrameSizes()
        ladder = _ladder(fps=30, seconds=10, frame_sizes=frame_sizes)

        await ladder.plan(max_quality=95, budget=BUDGET)
        await ladder.plan(max_quality=95, budget=BUDGET // 2)

        assert len(frame_sizes.measured) == len(set(frame_sizes.measured))
