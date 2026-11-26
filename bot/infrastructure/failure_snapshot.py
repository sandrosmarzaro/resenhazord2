import inspect
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar

from bot.data.telemetry_privacy import SECRET_NAME_PARTS
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class FailureSnapshot:
    """What a command raised, redacted: type, message, stack and the failing frame.

    The frame is the deepest one in the bot's own code, since the deepest overall is
    usually inside httpx or another library and says little about the call.
    """

    MAX_STACK_CHARS: ClassVar[int] = 6000
    MAX_ARGUMENTS: ClassVar[int] = 12
    _BOT_ROOT: ClassVar[str] = str(Path(__file__).resolve().parents[1])
    _RECEIVERS: ClassVar[frozenset[str]] = frozenset({'self', 'cls'})
    # Only plain values are shown: an object's repr can hold anything, a push name or
    # a quoted message among them, so it shows as its type.
    _SHOWN_TYPES: ClassVar[tuple[type, ...]] = (str, int, float, bool, bytes, type(None))

    @classmethod
    def of(cls, error: BaseException) -> dict[str, Any]:
        stack = ''.join(traceback.format_exception(error))
        return {
            'type': type(error).__name__,
            'message': TelemetryRedactor.value(str(error)),
            # Redacted whole, then cut to the tail, where the failure is.
            'stack': TelemetryRedactor.text(stack)[-cls.MAX_STACK_CHARS :],
            'frame': cls._frame(error.__traceback__),
        }

    @classmethod
    def _frame(cls, step: TracebackType | None) -> dict[str, Any] | None:
        deepest = None
        while step is not None:
            if step.tb_frame.f_code.co_filename.startswith(cls._BOT_ROOT):
                deepest = step
            step = step.tb_next
        if deepest is None:
            return None
        frame = deepest.tb_frame
        info = inspect.getargvalues(frame)
        names = [*info.args, *filter(None, (info.varargs, info.keywords))]
        shown = [name for name in names if name not in cls._RECEIVERS][: cls.MAX_ARGUMENTS]
        return {
            'function': frame.f_code.co_qualname,
            'line': deepest.tb_lineno,
            'arguments': {name: cls._argument(name, info.locals[name]) for name in shown},
        }

    @classmethod
    def _argument(cls, name: str, value: object) -> str:
        if any(part in name.lower() for part in SECRET_NAME_PARTS):
            return TelemetryRedactor.REDACTED
        if isinstance(value, cls._SHOWN_TYPES):
            return TelemetryRedactor.value(value)
        return f'<{type(value).__name__}>'
