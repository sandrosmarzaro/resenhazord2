"""JID (Jabber ID) utilities for WhatsApp identifiers."""

import re
from collections.abc import Iterable

_JID_SUFFIX_RE = re.compile(r'@lid|@s\.whatsapp\.net', re.IGNORECASE)
_DEVICE_SUFFIX_RE = re.compile(r':\d+(?=@)')


def strip_jid(jid: str) -> str:
    """Remove the @lid or @s.whatsapp.net suffix from a JID."""
    return _JID_SUFFIX_RE.sub('', jid)


def normalize_jid(jid: str) -> str:
    """Remove device suffix (e.g. :1) but keep domain suffix.

    WhatsApp JIDs may include a device identifier before the domain:
    ``5511999990000:1@s.whatsapp.net`` → ``5511999990000@s.whatsapp.net``.
    Normalising before storage/query guarantees that the same user is
    matched regardless of which device sent the message.
    """
    return _DEVICE_SUFFIX_RE.sub('', jid)


def normalize_jids(jids: Iterable[str | None]) -> list[str]:
    """Normalise a batch of JIDs, dropping the empty ones.

    WhatsApp mention lists arrive from the gateway and may carry null entries;
    storing one poisons every later render of that mention group.
    """
    return [normalize_jid(jid) for jid in jids if jid]
