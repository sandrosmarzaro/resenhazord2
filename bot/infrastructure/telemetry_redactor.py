import hashlib
import hmac
import re
import reprlib
import secrets
from typing import ClassVar

from bot.data.telemetry_privacy import PROVIDER_KEY_PREFIXES, SECRET_NAME_PARTS


class _RedactingRepr(reprlib.Repr):
    # reprlib cuts a bytes repr only after building it, and a video buffer is megabytes.
    def repr_bytes(self, value: bytes, _level: int) -> str:
        return f'<{len(value)} bytes>'

    # reprlib keeps a long string's head and tail, which can split a name from its
    # secret; each string is redacted whole before it is cut.
    def repr_str(self, value: str, _level: int) -> str:
        redacted = TelemetryRedactor.text(value[: TelemetryRedactor.MAX_INPUT_CHARS])
        return repr(redacted)[: self.maxstring]


class TelemetryRedactor:
    """Keeps credentials and chat identities out of anything a public issue shows.

    Identities are hashed with a key drawn at startup: a plain hash of a phone number
    is reversed by enumerating numbers, a keyed one is not. The same id hashes the
    same for the life of the process, which covers every id in one record.

    Every pattern runs in linear time: a token can only start where the previous
    character can't continue it, and its quantifiers are possessive, so an input
    crafted to backtrack costs one pass.
    """

    MAX_CHARS: ClassVar[int] = 300
    # Redaction runs on this much of a value before the cut, so the cut never splits a
    # secret the patterns would have caught.
    MAX_INPUT_CHARS: ClassVar[int] = 4096
    HASH_CHARS: ClassVar[int] = 10
    PHONE_MIN_DIGITS: ClassVar[int] = 10
    REDACTED: ClassVar[str] = '<redacted>'
    _KEY: ClassVar[bytes] = secrets.token_bytes(32)
    # Each element is capped and the nesting is shallow, so the whole repr is bounded
    # before it is cut to MAX_INPUT_CHARS.
    _REPR: ClassVar[reprlib.Repr] = _RedactingRepr(maxstring=1024, maxother=1024, maxlevel=2)
    _URL: ClassVar[re.Pattern[str]] = re.compile(
        r'(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*+://)([^\s\'"<>]*+)'
    )
    _QUERY: ClassVar[re.Pattern[str]] = re.compile(r'\?[\w.-]++=[^\s\'"<>]*+')
    _SECRETS: ClassVar[tuple[tuple[re.Pattern[str], str], ...]] = (
        (re.compile(r'bot\d++:[\w-]++'), f'bot{REDACTED}'),
        (re.compile(r'(?<!\d)\d{6,}+:[\w-]{30,}+'), REDACTED),
        (re.compile(r'(?i)\b(bearer|basic)\s++[\w.~+/=-]{8,}+'), rf'\1 {REDACTED}'),
        (
            re.compile(rf'(?<!\w)(?:{"|".join(map(re.escape, PROVIDER_KEY_PREFIXES))})[\w-]++'),
            REDACTED,
        ),
        (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), REDACTED),
    )
    # A name, its separator and its value; the name is checked in Python.
    _NAMED_VALUE: ClassVar[re.Pattern[str]] = re.compile(
        r'(?<![\w-])([\w-]++)(["\']?\s*+[:=]\s*+["\']?)([^"\'\s,&;}]++)'
    )
    # A WhatsApp JID or LID of any length, an old-style group id, or a run of digits
    # and separators that reads as a phone number.
    _IDENTITY: ClassVar[re.Pattern[str]] = re.compile(
        r'(?<!\d)(?:\d++-\d++@g\.us'
        r'|\d{6,}+(?::\d++)?@(?:s\.whatsapp\.net|lid|g\.us|c\.us)'
        r'|\+?\d[\d\s().-]{8,}\d)'
    )

    @classmethod
    def text(cls, value: str) -> str:
        value = cls._URL.sub(cls._strip_url, value)
        value = cls._QUERY.sub(f'?{cls.REDACTED}', value)
        for pattern, replacement in cls._SECRETS:
            value = pattern.sub(replacement, value)
        value = cls._NAMED_VALUE.sub(cls._hide_named_value, value)
        return cls._IDENTITY.sub(cls._hash_identity, value)

    @classmethod
    def identity(cls, value: str) -> str:
        digest = hmac.new(cls._KEY, value.encode(), hashlib.sha256).hexdigest()
        return digest[: cls.HASH_CHARS]

    @classmethod
    def value(cls, value: object) -> str:
        shown = value if isinstance(value, str) else cls._REPR.repr(value)
        return cls.text(shown[: cls.MAX_INPUT_CHARS])[: cls.MAX_CHARS]

    @classmethod
    def _strip_url(cls, match: re.Match[str]) -> str:
        # Userinfo is everything up to the authority's last @, so a password holding @,
        # :, ? or # goes whole; then the query string and the fragment are dropped.
        scheme, rest = match.groups()
        authority, slash, path = rest.partition('/')
        if '@' in authority:
            authority = f'{cls.REDACTED}@{authority.rpartition("@")[2]}'
        rest = authority + slash + path
        for mark in '?#':
            head, found, _ = rest.partition(mark)
            rest = head + (f'{mark}{cls.REDACTED}' if found else '')
        return scheme + rest

    @classmethod
    def _hide_named_value(cls, match: re.Match[str]) -> str:
        name, separator, _ = match.groups()
        if not any(part in name.lower() for part in SECRET_NAME_PARTS):
            return match.group()
        return f'{name}{separator}{cls.REDACTED}'

    @classmethod
    def _hash_identity(cls, match: re.Match[str]) -> str:
        found = match.group()
        # A date or a short count matches the phone shape with too few digits to dial.
        if '@' not in found and sum(char.isdigit() for char in found) < cls.PHONE_MIN_DIGITS:
            return found
        return f'<id:{cls.identity(found)}>'
