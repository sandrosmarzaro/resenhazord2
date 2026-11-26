import hashlib
import hmac
import re
import reprlib
import secrets
from typing import ClassVar

from bot.data.telemetry_privacy import PROVIDER_KEY_PREFIXES, SECRET_NAME_PARTS


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
    # Redaction runs on this much of a value before the cut, so the cut never splits a
    # secret the patterns would have caught.
    MAX_INPUT_CHARS: ClassVar[int] = 4096
    HASH_CHARS: ClassVar[int] = 10
    PHONE_MIN_DIGITS: ClassVar[int] = 10
    _KEY: ClassVar[bytes] = secrets.token_bytes(32)
    _REPR: ClassVar[reprlib.Repr] = _BoundedRepr(
        maxstring=MAX_INPUT_CHARS, maxother=MAX_INPUT_CHARS
    )
    _SECRETS: ClassVar[tuple[tuple[re.Pattern[str], str], ...]] = (
        # Userinfo runs to the last @ of the authority, so a password with @ or : in it,
        # or a bare username, goes whole.
        (re.compile(r'(?i)\b([a-z][a-z0-9+.-]*://)[^/\s?#]*@'), r'\1<redacted>@'),
        # A query string is dropped whole: its credentials have too many names to list.
        (re.compile(r'(?i)(\b[a-z][a-z0-9+.-]*://[^\s?#\'"]*)\?[^\s#\'"<>]*'), r'\1?<redacted>'),
        (re.compile(r'bot\d+:[\w-]+'), 'bot<redacted>'),
        (re.compile(r'\b\d{6,}:[\w-]{30,}'), '<redacted>'),
        (re.compile(r'(?i)\b(bearer|basic)\s+[\w.~+/=-]{8,}'), r'\1 <redacted>'),
        (
            re.compile(rf'\b(?:{"|".join(map(re.escape, PROVIDER_KEY_PREFIXES))})[\w-]+'),
            '<redacted>',
        ),
        (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), '<redacted>'),
        (
            re.compile(
                rf'(?i)(\b[\w-]*(?:{"|".join(SECRET_NAME_PARTS)})[\w-]*["\']?\s*[:=]\s*["\']?)'
                r'[^"\'\s,&;}]+'
            ),
            r'\1<redacted>',
        ),
    )
    # A WhatsApp JID or LID of any length, an old-style group id, or a run of digits
    # and separators that reads as a phone number.
    _IDENTITY: ClassVar[re.Pattern[str]] = re.compile(
        r'\d+-\d+@g\.us'
        r'|\d{6,}(?::\d+)?@(?:s\.whatsapp\.net|lid|g\.us|c\.us)'
        r'|\+?\d[\d\s().-]{8,}\d'
    )

    @classmethod
    def text(cls, value: str) -> str:
        for pattern, replacement in cls._SECRETS:
            value = pattern.sub(replacement, value)
        return cls._IDENTITY.sub(cls._hash_identity, value)

    @classmethod
    def identity(cls, value: str) -> str:
        digest = hmac.new(cls._KEY, value.encode(), hashlib.sha256).hexdigest()
        return digest[: cls.HASH_CHARS]

    @classmethod
    def value(cls, value: object) -> str:
        shown = value[: cls.MAX_INPUT_CHARS] if isinstance(value, str) else cls._REPR.repr(value)
        return cls.text(shown)[: cls.MAX_CHARS]

    @classmethod
    def _hash_identity(cls, match: re.Match[str]) -> str:
        found = match.group()
        # A date or a short count matches the phone shape with too few digits to dial.
        if '@' not in found and sum(char.isdigit() for char in found) < cls.PHONE_MIN_DIGITS:
            return found
        return f'<id:{cls.identity(found)}>'
