import pytest

from bot.adapters.discord.music.queue import LoopMode, MusicQueue
from bot.domain.models.track import Track


def _track(title: str = 'Song', index: int = 0) -> Track:
    return Track(
        title=f'{title} {index}',
        author='Artist',
        url=f'https://youtube.com/watch?v={index}',
        stream_url=f'https://stream/{index}',
        duration=180,
        thumbnail=f'https://thumb/{index}.jpg',
        requested_by='User',
        requested_by_id=1,
    )


class TestAdd:
    def test_add_returns_position(self):
        queue = MusicQueue()

        assert queue.add(_track(index=0)) == 0
        assert queue.add(_track(index=1)) == 1
        assert queue.add(_track(index=2)) == 2

    def test_add_many_returns_count(self):
        queue = MusicQueue()
        tracks = [_track(index=i) for i in range(5)]

        assert queue.add_many(tracks) == 5
        assert queue.size == 5


class TestReplaceCurrent:
    def test_replaces_current_track(self):
        queue = MusicQueue()
        queue.add(_track(index=0))
        queue.add(_track(index=1))

        replacement = _track(title='Resolved', index=0)
        queue.replace_current(replacement)

        assert queue.current == replacement

    def test_noop_on_empty_queue(self):
        queue = MusicQueue()

        queue.replace_current(_track(index=0))

        assert queue.is_empty


class TestCurrent:
    def test_current_returns_first_track(self):
        queue = MusicQueue()
        track = _track(index=0)
        queue.add(track)

        assert queue.current == track

    def test_current_returns_none_when_empty(self):
        queue = MusicQueue()

        assert queue.current is None


class TestProperties:
    def test_is_empty(self):
        queue = MusicQueue()

        assert queue.is_empty is True

        queue.add(_track())

        assert queue.is_empty is False

    def test_tracks_returns_copy(self):
        queue = MusicQueue()
        track = _track()
        queue.add(track)
        tracks = queue.tracks

        tracks.clear()

        assert queue.size == 1

    def test_upcoming_returns_tracks_after_current(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))

        upcoming = queue.upcoming

        assert len(upcoming) == 2
        assert upcoming[0].title == 'Song 1'
        assert upcoming[1].title == 'Song 2'

    def test_upcoming_empty_when_at_last(self):
        queue = MusicQueue()
        queue.add(_track(index=0))

        assert queue.upcoming == []


class TestAdvance:
    def test_advance_to_next(self):
        queue = MusicQueue()
        queue.add(_track(index=0))
        queue.add(_track(index=1))

        result = queue.advance()

        assert result is not None
        assert result.title == 'Song 1'
        assert queue.current_index == 1

    def test_advance_returns_none_at_end(self):
        queue = MusicQueue()
        queue.add(_track(index=0))

        result = queue.advance()

        assert result is None

    def test_advance_returns_none_when_empty(self):
        queue = MusicQueue()

        assert queue.advance() is None

    def test_advance_with_loop_track_repeats(self):
        queue = MusicQueue()
        track = _track(index=0)
        queue.add(track)
        queue.add(_track(index=1))
        queue.cycle_loop()

        result = queue.advance()

        assert result == track
        assert queue.current_index == 0

    def test_advance_with_loop_queue_wraps(self):
        queue = MusicQueue()
        queue.add(_track(index=0))
        queue.add(_track(index=1))
        queue.cycle_loop()
        queue.cycle_loop()
        queue.advance()

        result = queue.advance()

        assert result is not None
        assert result.title == 'Song 0'
        assert queue.current_index == 0


class TestBack:
    def test_back_to_previous(self):
        queue = MusicQueue()
        queue.add(_track(index=0))
        queue.add(_track(index=1))
        queue.advance()

        result = queue.back()

        assert result is not None
        assert result.title == 'Song 0'
        assert queue.current_index == 0

    def test_back_returns_none_at_start(self):
        queue = MusicQueue()
        queue.add(_track(index=0))

        assert queue.back() is None

    def test_back_returns_none_when_empty(self):
        queue = MusicQueue()

        assert queue.back() is None


class TestRemove:
    def test_remove_returns_track(self):
        queue = MusicQueue()
        track = _track(index=0)
        queue.add(track)

        assert queue.remove(0) == track
        assert queue.is_empty

    def test_remove_invalid_index_returns_none(self):
        queue = MusicQueue()

        assert queue.remove(0) is None
        assert queue.remove(-1) is None

    def test_remove_before_current_adjusts_index(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))
        queue.advance()

        queue.remove(0)

        assert queue.current_index == 0
        assert queue.current is not None
        assert queue.current.title == 'Song 1'

    def test_remove_after_current_keeps_index(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))

        queue.remove(2)

        assert queue.current_index == 0
        assert queue.size == 2


class TestMove:
    def test_move_to_top(self):
        queue = MusicQueue()
        for i in range(4):
            queue.add(_track(index=i))

        result = queue.move_to_top(3)

        assert result is True
        assert queue.tracks[1].title == 'Song 3'

    def test_move_to_top_invalid_index(self):
        queue = MusicQueue()

        assert queue.move_to_top(5) is False

    def test_move_to_top_already_next(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))

        assert queue.move_to_top(1) is False

    def test_move_to_bottom(self):
        queue = MusicQueue()
        for i in range(4):
            queue.add(_track(index=i))

        result = queue.move_to_bottom(1)

        assert result is True
        assert queue.tracks[-1].title == 'Song 1'

    def test_move_to_bottom_already_last(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))

        assert queue.move_to_bottom(2) is False

    def test_move_to_bottom_before_current_adjusts_index(self):
        queue = MusicQueue()
        for i in range(4):
            queue.add(_track(index=i))
        queue.advance()

        queue.move_to_bottom(0)

        assert queue.current_index == 0
        assert queue.current is not None
        assert queue.current.title == 'Song 1'


class TestClear:
    def test_clear_resets_queue(self):
        queue = MusicQueue()
        for i in range(3):
            queue.add(_track(index=i))
        queue.advance()

        queue.clear()

        assert queue.is_empty
        assert queue.current_index == 0


class TestShuffle:
    def test_shuffle_preserves_current(self):
        queue = MusicQueue()
        for i in range(10):
            queue.add(_track(index=i))
        queue.advance()
        current = queue.current

        queue.shuffle()

        assert queue.current == current

    def test_shuffle_does_nothing_with_one_track(self):
        queue = MusicQueue()
        queue.add(_track(index=0))

        queue.shuffle()

        assert queue.size == 1


class TestVolume:
    def test_default_volume(self):
        queue = MusicQueue()

        assert queue.volume == pytest.approx(MusicQueue.DEFAULT_VOLUME)

    def test_volume_up(self):
        queue = MusicQueue()

        new_vol = queue.volume_up()

        assert new_vol == pytest.approx(MusicQueue.DEFAULT_VOLUME + MusicQueue.VOLUME_STEP)

    def test_volume_down(self):
        queue = MusicQueue()

        new_vol = queue.volume_down()

        assert new_vol == pytest.approx(MusicQueue.DEFAULT_VOLUME - MusicQueue.VOLUME_STEP)

    def test_volume_capped_at_max(self):
        queue = MusicQueue()
        for _ in range(20):
            queue.volume_up()

        assert queue.volume == pytest.approx(MusicQueue.MAX_VOLUME)

    def test_volume_capped_at_min(self):
        queue = MusicQueue()
        for _ in range(20):
            queue.volume_down()

        assert queue.volume == pytest.approx(MusicQueue.MIN_VOLUME)


class TestLoopMode:
    def test_default_loop_off(self):
        queue = MusicQueue()

        assert queue.loop_mode == LoopMode.OFF

    def test_cycle_loop(self):
        queue = MusicQueue()

        assert queue.cycle_loop() == LoopMode.TRACK
        assert queue.cycle_loop() == LoopMode.QUEUE
        assert queue.cycle_loop() == LoopMode.OFF
