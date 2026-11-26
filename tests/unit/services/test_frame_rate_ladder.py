import pytest

from bot.domain.exceptions import StickerTooLargeError
from bot.domain.services.sticker.frame_rate_ladder import EncodePlan, FrameRateLadder
from bot.domain.services.sticker.video_clip import VideoClip

BUDGET = 500_000
BYTES_PER_QUALITY_POINT = 100


class FrameSizes:
    def __init__(
        self, bytes_per_quality_point: int = BYTES_PER_QUALITY_POINT, base: int = 0, power: int = 1
    ) -> None:
        self.bytes_per_quality_point = bytes_per_quality_point
        self.base = base
        self.power = power
        self.measured: list[int] = []

    async def __call__(self, quality: int) -> int:
        self.measured.append(quality)
        return self.base + quality**self.power * self.bytes_per_quality_point


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

        # 3 frames fit up to q55: the first step's q50 floor fits, q95 doesn't.
        await _ladder(fps=30, seconds=0.1, frame_sizes=frame_sizes).plan(
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


class Encodes:
    def __init__(self, *sizes: int) -> None:
        self.sizes = list(sizes)
        self.plans: list[EncodePlan] = []

    async def __call__(self, plan: EncodePlan) -> bytes:
        self.plans.append(plan)
        size = self.sizes.pop(0) if len(self.sizes) > 1 else self.sizes[0]
        return b'x' * size


class TestSearchCost:
    @pytest.mark.anyio
    async def test_tries_at_most_a_few_qualities_between_the_floor_and_the_cap(self) -> None:
        # Real sizes grow faster at high qualities, which slows an interpolation down.
        frame_sizes = FrameSizes(bytes_per_quality_point=1, power=3)

        # 3 frames fit up to q55: the first step's q50 floor fits, q95 doesn't.
        await _ladder(fps=30, seconds=0.1, frame_sizes=frame_sizes).plan(
            max_quality=95, budget=BUDGET
        )

        lowest_cap_and_floor = 3
        assert len(frame_sizes.measured) <= lowest_cap_and_floor + FrameRateLadder.MAX_PROBES


class TestFit:
    @pytest.mark.anyio
    async def test_aims_under_the_limit_at_first(self) -> None:
        # 300 frames of 1.65 kB are 495 kB: under the limit, not under its margin.
        encodes = Encodes(BUDGET - 1_000)
        ladder = _ladder(fps=30, seconds=10, frame_sizes=FrameSizes(0, base=1_650))

        await ladder.fit(max_quality=95, encode=encodes)

        assert [plan.fps for plan in encodes.plans] == [24]

    @pytest.mark.anyio
    async def test_keeps_an_encode_that_fills_the_budget(self) -> None:
        encodes = Encodes(BUDGET - 1_000)

        sticker = await _ladder(fps=30, seconds=10).fit(max_quality=95, encode=encodes)

        assert len(sticker) == BUDGET - 1_000
        assert len(encodes.plans) == 1

    @pytest.mark.anyio
    async def test_aims_lower_when_the_encode_is_over_the_limit(self) -> None:
        encodes = Encodes(BUDGET * 6 // 5, BUDGET - 1_000)
        ladder = _ladder(fps=30, seconds=10, frame_sizes=FrameSizes(0, base=1_600))

        sticker = await ladder.fit(max_quality=95, encode=encodes)

        assert len(sticker) == BUDGET - 1_000
        assert [plan.fps for plan in encodes.plans] == [30, 24]

    @pytest.mark.anyio
    async def test_aims_lower_by_how_far_the_estimate_missed(self) -> None:
        # The plan was estimated at 480 kB and weighs 501 kB: 4% off, not the 0.2% it
        # went over the limit by.
        encodes = Encodes(501_000, BUDGET - 1_000)
        ladder = _ladder(fps=30, seconds=10, frame_sizes=FrameSizes(0, base=1_600))

        sticker = await ladder.fit(max_quality=95, encode=encodes)

        assert len(sticker) == BUDGET - 1_000
        assert [plan.fps for plan in encodes.plans] == [30, 24]

    @pytest.mark.anyio
    async def test_aims_higher_when_the_encode_leaves_room(self) -> None:
        # Frames weigh less once the encoder reuses what didn't change between them.
        encodes = Encodes(BUDGET * 3 // 5, BUDGET - 1_000)
        ladder = _ladder(fps=30, seconds=10, frame_sizes=FrameSizes(0, base=2_000))

        sticker = await ladder.fit(max_quality=95, encode=encodes)

        assert len(sticker) == BUDGET - 1_000
        assert [plan.fps for plan in encodes.plans] == [24, 30]

    @pytest.mark.anyio
    async def test_keeps_the_encode_that_fit_when_aiming_higher_overflows(self) -> None:
        encodes = Encodes(BUDGET * 3 // 5, BUDGET + 1)
        ladder = _ladder(fps=30, seconds=10, frame_sizes=FrameSizes(0, base=2_000))

        sticker = await ladder.fit(max_quality=95, encode=encodes)

        assert len(sticker) == BUDGET * 3 // 5

    @pytest.mark.anyio
    async def test_does_not_encode_again_at_the_best_plan(self) -> None:
        encodes = Encodes(BUDGET // 10)

        await _ladder(fps=30, seconds=1).fit(max_quality=95, encode=encodes)

        assert encodes.plans == [EncodePlan(fps=30, quality=95)]

    @pytest.mark.anyio
    async def test_refuses_when_every_encode_is_over_the_limit(self) -> None:
        encodes = Encodes(BUDGET * 2)
        ladder = _ladder(fps=30, seconds=10, frame_sizes=FrameSizes(0, base=1_600))

        with pytest.raises(StickerTooLargeError):
            await ladder.fit(max_quality=95, encode=encodes)

        assert len(encodes.plans) == FrameRateLadder.MAX_ENCODES
