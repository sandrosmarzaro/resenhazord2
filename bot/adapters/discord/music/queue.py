import random
from enum import StrEnum
from typing import ClassVar

from bot.domain.models.track import Track


class LoopMode(StrEnum):
    OFF = 'off'
    TRACK = 'track'
    QUEUE = 'queue'


class MusicQueue:
    DEFAULT_VOLUME: ClassVar[float] = 0.5
    VOLUME_STEP: ClassVar[float] = 0.1
    MIN_VOLUME: ClassVar[float] = 0.0
    MAX_VOLUME: ClassVar[float] = 1.0
    LOOP_CYCLE: ClassVar[dict[LoopMode, LoopMode]] = {
        LoopMode.OFF: LoopMode.TRACK,
        LoopMode.TRACK: LoopMode.QUEUE,
        LoopMode.QUEUE: LoopMode.OFF,
    }

    def __init__(self) -> None:
        self._tracks: list[Track] = []
        self._current_index: int = 0
        self._loop_mode: LoopMode = LoopMode.OFF
        self._volume: float = self.DEFAULT_VOLUME

    @property
    def current(self) -> Track | None:
        if not self._tracks or self._current_index >= len(self._tracks):
            return None
        return self._tracks[self._current_index]

    @property
    def is_empty(self) -> bool:
        return len(self._tracks) == 0

    @property
    def tracks(self) -> list[Track]:
        return list(self._tracks)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def size(self) -> int:
        return len(self._tracks)

    @property
    def upcoming(self) -> list[Track]:
        if self._current_index + 1 >= len(self._tracks):
            return []
        return list(self._tracks[self._current_index + 1 :])

    def replace_current(self, track: Track) -> None:
        if self._tracks and self._current_index < len(self._tracks):
            self._tracks[self._current_index] = track

    def add(self, track: Track) -> int:
        self._tracks.append(track)
        return len(self._tracks) - 1

    def add_many(self, tracks: list[Track]) -> int:
        self._tracks.extend(tracks)
        return len(tracks)

    def remove(self, index: int) -> Track | None:
        if index < 0 or index >= len(self._tracks):
            return None

        track = self._tracks.pop(index)

        if index < self._current_index:
            self._current_index -= 1
        elif index == self._current_index and self._current_index >= len(self._tracks):
            self._current_index = max(0, len(self._tracks) - 1)

        return track

    def move_to_top(self, index: int) -> bool:
        if index < 0 or index >= len(self._tracks):
            return False

        next_index = self._current_index + 1
        if index <= next_index:
            return False

        track = self._tracks.pop(index)
        self._tracks.insert(next_index, track)

        return True

    def move_to_bottom(self, index: int) -> bool:
        if index < 0 or index >= len(self._tracks):
            return False
        if index == len(self._tracks) - 1:
            return False

        track = self._tracks.pop(index)
        self._tracks.append(track)

        if index < self._current_index:
            self._current_index -= 1

        return True

    def advance(self) -> Track | None:
        if self.is_empty:
            return None

        if self._loop_mode == LoopMode.TRACK:
            return self.current

        next_index = self._current_index + 1

        if next_index >= len(self._tracks):
            if self._loop_mode == LoopMode.QUEUE:
                self._current_index = 0
                return self.current
            return None

        self._current_index = next_index
        return self.current

    def back(self) -> Track | None:
        if self.is_empty or self._current_index == 0:
            return None

        self._current_index -= 1
        return self.current

    def clear(self) -> None:
        self._tracks.clear()
        self._current_index = 0

    def shuffle(self) -> None:
        if len(self._tracks) <= 1:
            return

        current = self.current
        upcoming = self._tracks[self._current_index + 1 :]
        random.shuffle(upcoming)
        self._tracks[self._current_index + 1 :] = upcoming

        if current and self._tracks[self._current_index] != current:
            idx = self._tracks.index(current)
            self._tracks[self._current_index], self._tracks[idx] = (
                self._tracks[idx],
                self._tracks[self._current_index],
            )

    @property
    def volume(self) -> float:
        return self._volume

    def volume_up(self) -> float:
        self._volume = min(self._volume + self.VOLUME_STEP, self.MAX_VOLUME)
        return self._volume

    def volume_down(self) -> float:
        self._volume = max(self._volume - self.VOLUME_STEP, self.MIN_VOLUME)
        return self._volume

    @property
    def loop_mode(self) -> LoopMode:
        return self._loop_mode

    def cycle_loop(self) -> LoopMode:
        self._loop_mode = self.LOOP_CYCLE[self._loop_mode]
        return self._loop_mode
