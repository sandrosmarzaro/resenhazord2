import threading
from typing import Any, ClassVar


class TelemetryBuffer:
    """Spans or log lines one command produced, bounded so a bug report never leaks.

    Each buffer keeps at most `limit` entries, and every open buffer together at most
    GLOBAL_LIMIT, so a burst of concurrent commands is capped too. An entry past either
    cap is counted as dropped. Draining closes the buffer and returns its share of the
    global budget, and a closed buffer takes nothing more, so a task that outlives its
    command can't grow it.
    """

    PER_COMMAND_LIMIT: ClassVar[int] = 64
    GLOBAL_LIMIT: ClassVar[int] = 1024
    # Spans end on worker threads too, so the shared count needs a lock.
    _LOCK: ClassVar[threading.Lock] = threading.Lock()
    _held: ClassVar[int] = 0

    def __init__(self, limit: int = PER_COMMAND_LIMIT) -> None:
        self._limit = limit
        self._entries: list[dict[str, Any]] = []
        self._dropped = 0
        self._closed = False

    @classmethod
    def held(cls) -> int:
        return cls._held

    def append(self, entry: dict[str, Any]) -> None:
        with self._LOCK:
            full = len(self._entries) >= self._limit or self._held >= self.GLOBAL_LIMIT
            if self._closed or full:
                self._dropped += 1
                return
            self._entries.append(entry)
            TelemetryBuffer._held += 1

    def drain(self) -> tuple[list[dict[str, Any]], int]:
        with self._LOCK:
            entries, self._entries = self._entries, []
            TelemetryBuffer._held -= len(entries)
            self._closed = True
            return entries, self._dropped
