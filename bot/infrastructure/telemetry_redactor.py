import hashlib
import hmac
import re
import reprlib
import secrets
from typing import ClassVar

from bot.data.telemetry_privacy import SECRET_QUERY_KEYS


class _BoundedRepr(reprlib.Repr):
    # reprlib cuts a bytes repr only after building it, and a video buffer is megabytes.
    def repr_bytes(self, value: bytes, _level: int) -> str:
        return f'<{len(value)} bytes>'


class TelemetryRedactor:
    """Keeps credentials and chat identities out of anything a public issue shows.

    Identities are hashed with a key drawn at startup: a plain hash of a phone number
    is reversed by enumerating numbers, a keyed one is not. The same id hashes the
    same for the life of the process, which covers every id in one record.
    """

    MAX_CHARS: ClassVar[int] = 300
    HASH_CHARS: ClassVar[int] = 10
    _KEY: ClassVar[bytes] = secrets.token_bytes(32)
    _REPR: ClassVar[reprlib.Repr] = _BoundedRepr(maxstring=MAX_CHARS, maxother=MAX_CHARS)
    _SECRETS: ClassVar[tuple[tuple[re.Pattern[str], str], ...]] = (
        (re.compile(r'bot\d+:[\w-]+'), 'bot<redacted>'),
        (re.compile(r'://[^/\s:@]+:[^/\s@]+@'), '://<redacted>@'),
        (re.compile(r'(?i)\b(bearer|basic)\s+[\w.~+/=-]{8,}'), r'\1 <redacted>'),
        (re.compile(r'\b(?:gh[pousr]_|github_pat_)\w+'), '<redacted>'),
        (
            re.compile(rf'(?i)([?&;](?:{"|".join(SECRET_QUERY_KEYS)})=)[^&\s#"\']+'),
            r'\1<redacted>',
        ),
    )
    # A WhatsApp JID or LID, an old-style group id, or a bare number long enough to be a
    # phone, a Discord snowflake or a Telegram chat.
    _IDENTITY: ClassVar[re.Pattern[str]] = re.compile(
        r'\d+-\d+@g\.us|\+?\b\d{10,}(?::\d+)?(?:@(?:s\.whatsapp\.net|lid|g\.us|c\.us))?'
    )

    @classmethod
    def text(cls, value: str) -> str:
        for pattern, replacement in cls._SECRETS:
            value = pattern.sub(replacement, value)
        return cls._IDENTITY.sub(lambda match: f'<id:{cls.identity(match.group())}>', value)

    @classmethod
    def identity(cls, value: str) -> str:
        digest = hmac.new(cls._KEY, value.encode(), hashlib.sha256).hexdigest()
        return digest[: cls.HASH_CHARS]

    @classmethod
    def value(cls, value: object) -> str:
        shown = value if isinstance(value, str) else cls._REPR.repr(value)
        return cls.text(shown)[: cls.MAX_CHARS]
