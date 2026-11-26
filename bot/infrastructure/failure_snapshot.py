import inspect
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar

from bot.domain.exceptions import BotError
from bot.infrastructure.telemetry_field_policy import TelemetryFieldPolicy
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class FailureSnapshot:
    """What a command raised, as much as a public issue may show.

    The message is short and redacted (a BotError shows the reply the user got, not
    its detail). The stack keeps only where each frame was, file, line and function,
    for the whole exception chain: no source lines and no chained messages. The frame
    is the deepest one in the bot's own code, since the deepest overall is usually
    inside a library and says little about the call.
    """

    MAX_MESSAGE_CHARS: ClassVar[int] = 120
    MAX_STACK_CHARS: ClassVar[int] = 6000
    MAX_ARGUMENTS: ClassVar[int] = 12
    _BOT_ROOT: ClassVar[str] = str(Path(__file__).resolve().parents[1])
    _RECEIVERS: ClassVar[frozenset[str]] = frozenset({'self', 'cls'})
    _PACKAGES: ClassVar[str] = 'site-packages/'

    @classmethod
    def of(cls, error: BaseException) -> dict[str, Any]:
        message = error.user_message if isinstance(error, BotError) else str(error)
        return {
            'type': type(error).__name__,
            'message': TelemetryRedactor.value(message)[: cls.MAX_MESSAGE_CHARS],
            'stack': cls._stack(error)[-cls.MAX_STACK_CHARS :],
            'frame': cls._frame(error.__traceback__),
        }

    @classmethod
    def _stack(cls, error: BaseException) -> str:
        chain: list[BaseException] = []
        current: BaseException | None = error
        while current is not None and current not in chain:
            chain.append(current)
            current = current.__cause__ or (
                None if current.__suppress_context__ else current.__context__
            )
        # Oldest cause first, the way Python prints a chain.
        lines = []
        for link in reversed(chain):
            lines.append(type(link).__name__)
            lines.extend(
                f'  {cls._where(frame.filename)}:{frame.lineno} in {frame.name}'
                for frame in traceback.extract_tb(link.__traceback__)
            )
        return TelemetryRedactor.text('\n'.join(lines))

    @classmethod
    def _where(cls, filename: str) -> str:
        if filename.startswith(cls._BOT_ROOT):
            return f'bot{filename.removeprefix(cls._BOT_ROOT)}'
        _, found, inside = filename.rpartition(cls._PACKAGES)
        return inside if found else Path(filename).name

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

    @staticmethod
    def _argument(name: str, value: object) -> str:
        shown = TelemetryFieldPolicy.show(name, value)
        if shown is not None:
            return shown
        # Off the allowlist, only the shape: a string's content is the chat's.
        if isinstance(value, str):
            return f'<str len={len(value)}>'
        return f'<{type(value).__name__}>'
