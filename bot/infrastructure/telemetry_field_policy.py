from typing import ClassVar
from urllib.parse import urlsplit

from bot.data.telemetry_privacy import IDENTITY_FIELDS, SAFE_FIELDS, SECRET_NAME_PARTS, URL_FIELDS
from bot.infrastructure.telemetry_redactor import TelemetryRedactor


class TelemetryFieldPolicy:
    """The one rule for a named value leaving the process: hide, hash, show or drop.

    Log fields, span attributes and frame arguments all go through it. A secret name
    wins over everything, then an identity, then the allowlist, which shows only plain
    values; any other name is dropped, so a field nobody vetted never reaches a public
    issue.
    """

    _IDENTITY_SUFFIXES: ClassVar[tuple[str, ...]] = ('_id', 'jid')
    # An allowed name shows its value only when the value is plain: an object's repr
    # can hold anything, a JID or a token among them.
    _PLAIN_TYPES: ClassVar[tuple[type, ...]] = (str, int, float, bool, type(None))

    @classmethod
    def show(cls, name: str, value: object) -> str | None:
        lowered = name.lower()
        if any(part in lowered for part in SECRET_NAME_PARTS):
            return TelemetryRedactor.REDACTED
        # An id is hashed whole by its name: a Telegram or Discord id is too short for
        # the text patterns to tell it from any other number.
        if lowered in IDENTITY_FIELDS or lowered.endswith(cls._IDENTITY_SUFFIXES):
            return TelemetryRedactor.identity(str(value))
        if lowered in URL_FIELDS:
            return cls._url(str(value))
        if lowered not in SAFE_FIELDS:
            return None
        if isinstance(value, cls._PLAIN_TYPES):
            return TelemetryRedactor.value(value)
        return f'<{type(value).__name__}>'

    @staticmethod
    def _url(value: str) -> str:
        # Parsed, not matched: no userinfo, query string or fragment survives.
        url = urlsplit(value)
        host = url.hostname or ''
        netloc = f'{host}:{url.port}' if url.port else host
        return TelemetryRedactor.value(url._replace(netloc=netloc, query='', fragment='').geturl())
